import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file, session
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "hackathon-secret")
project_root = Path(__file__).resolve().parent
upload_dir = project_root / "uploads"
report_dir = project_root / "downloads"
upload_dir.mkdir(exist_ok=True)
report_dir.mkdir(exist_ok=True)

from ai.groq_client import GroqClient
from ai.pitch_generator import PitchGenerator
from ai.problem_analyzer import ProblemAnalyzer
from ai.solution_generator import SolutionGenerator
from ai.tech_recommender import TechRecommender
from rag.chunker import chunk_text
from rag.document_loader import extract_text_from_bytes
from rag.vector_store import LocalVectorStore
from utils.helpers import build_project_report
from utils.project_store import ProjectStore

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
project_store = ProjectStore(project_root / "data" / "projects.sqlite3")
SOLUTION_PROMPT_VERSION = 2


def new_project_state():
    return {
        "uploaded_documents": [],
        "rag_text": "",
        "problem_statements": [],
        "selected_problem": {},
        "solutions": [],
        "solutions_for_selection_key": "",
        "solution_generation_mode": "",
        "solution_prompt_version": SOLUTION_PROMPT_VERSION,
        "selected_solution": {},
        "tech_stack": {},
        "pitch": {},
        "chat_history": [
            {"role": "assistant", "message": "Welcome to the AI Hackathon Assistant. Upload a problem document and let’s begin."}
        ],
    }


def ensure_project_state():
    project_id = session.get("project_id")
    if not project_id:
        project_id = uuid.uuid4().hex
        session["project_id"] = project_id

    project = project_store.load(project_id)
    if project is None:
        project = new_project_state()
        project_store.save(project_id, project)
    elif project.get("solution_prompt_version") != SOLUTION_PROMPT_VERSION:
        project.update({
            "solutions": [],
            "solutions_for_selection_key": "",
            "solution_generation_mode": "",
            "solution_prompt_version": SOLUTION_PROMPT_VERSION,
            "selected_solution": {},
            "tech_stack": {},
            "pitch": {},
        })
        project_store.save(project_id, project)
    return project


def save_project_state(project):
    project_id = session.get("project_id")
    if not project_id:
        project_id = uuid.uuid4().hex
        session["project_id"] = project_id
    project_store.save(project_id, project)


def remove_stored_upload(project):
    stored_upload = project.get("stored_upload")
    if not stored_upload:
        return

    upload_path = (upload_dir / stored_upload).resolve()
    if upload_path.parent != upload_dir.resolve():
        raise ValueError("Stored upload path is outside the upload directory.")
    upload_path.unlink(missing_ok=True)


def get_vector_store():
    if not hasattr(app, "vector_store") or app.vector_store is None:
        app.vector_store = LocalVectorStore()
    return app.vector_store


def add_chat_message(role, message):
    project = ensure_project_state()
    project.setdefault("chat_history", [])
    project["chat_history"].append({"role": role, "message": message})
    project["chat_history"] = project["chat_history"][-20:]
    save_project_state(project)


@app.route("/")
def index():
    previous_project_id = session.pop("project_id", None)
    if previous_project_id:
        previous_project = project_store.load(previous_project_id)
        if previous_project:
            remove_stored_upload(previous_project)
        project_store.delete(previous_project_id)

    project_id = uuid.uuid4().hex
    session["project_id"] = project_id
    project_store.save(project_id, new_project_state())
    if app.vector_store is not None:
        app.vector_store.reset()
    return render_template("index.html")


@app.route("/api/project-state")
def project_state():
    project = ensure_project_state()
    public_project = {
        key: value for key, value in project.items()
        if key not in {"rag_text", "stored_upload"}
    }
    return jsonify({"project": public_project})


@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify({
        "status": "error",
        "message": "The uploaded file is too large. The maximum file size is 20 MB.",
    }), 413


@app.route("/api/upload-document", methods=["POST"])
def upload_document():
    project = ensure_project_state()
    uploaded_file = request.files.get("file")

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"status": "error", "message": "Please upload a PDF, DOCX, or TXT file."}), 400

    file_ext = Path(uploaded_file.filename).suffix.lower()
    if file_ext not in {".pdf", ".docx", ".txt"}:
        return jsonify({"status": "error", "message": "Unsupported file type. Upload PDF, DOCX, or TXT only."}), 400

    filename = secure_filename(uploaded_file.filename)
    if not filename:
        return jsonify({"status": "error", "message": "The uploaded filename is not valid."}), 400

    file_bytes = uploaded_file.stream.read()
    remove_stored_upload(project)
    project.update({
        "stored_upload": "",
        "uploaded_documents": [],
        "rag_text": "",
        "problem_statements": [],
        "solutions_for_selection_key": "",
        "solution_generation_mode": "",
        "selected_problem": {},
        "solutions": [],
        "selected_solution": {},
        "tech_stack": {},
        "pitch": {},
        "chat_history": [
            {"role": "assistant", "message": "Upload a problem document and let’s begin."}
        ],
    })
    save_project_state(project)

    if not file_bytes:
        return jsonify({
            "status": "error",
            "message": "The selected file is empty (0 bytes). Re-select the original document and upload it again.",
        }), 400

    try:
        text = extract_text_from_bytes(file_bytes, file_ext)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Could not read {filename}: {exc}",
        }), 400

    if not text.strip():
        return jsonify({
            "status": "error",
            "message": (
                f"No selectable text could be extracted from {filename}. "
                "If this PDF is a scan, run OCR or upload a text-based PDF, DOCX, or TXT file."
            ),
        }), 422

    save_path = upload_dir / f"{uuid.uuid4().hex}_{filename}"
    save_path.write_bytes(file_bytes)

    try:
        chunks = chunk_text(text)
        vector_store = get_vector_store()
        vector_store.reset()
        vector_store.add_texts(chunks)
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        return jsonify({
            "status": "error",
            "message": f"Could not prepare the document for analysis: {exc}",
        }), 500

    detected_count = len(ProblemAnalyzer().extract_candidates(text))
    project["uploaded_documents"] = [{
        "name": filename,
        "status": "Ready for AI Analysis" if detected_count else "Text extracted; problem statements not identified",
        "pages": max(1, len(text.splitlines()) // 30),
        "problem_statements_detected": detected_count,
    }]
    project["stored_upload"] = save_path.name
    project["rag_text"] = text
    save_project_state(project)

    return jsonify({
        "status": "success",
        "message": (
            "File uploaded and text extracted successfully."
            if detected_count
            else "File uploaded, but no recognizable problem statement fields were found. Check that the PDF contains selectable text and uses statement titles or IDs."
        ),
        "documents": project["uploaded_documents"],
        "problem_count": project["uploaded_documents"][0]["problem_statements_detected"],
    })


@app.route("/api/analyze-problem-statements", methods=["POST"])
def analyze_problem_statements():
    project = ensure_project_state()
    if not project.get("rag_text"):
        return jsonify({"status": "error", "message": "Upload a problem statement document first."}), 400

    team_profile = {
        "team_skills": request.form.get("team_skills", "Python, AI/ML, Web Development"),
        "preferred_domain": request.form.get("preferred_domain", "General"),
        "development_duration": request.form.get("development_duration", "6 Weeks"),
    }
    filters = {
        "preferred_domain": request.form.get("preferred_domain", "General"),
        "difficulty": request.form.get("difficulty", "Medium"),
        "development_duration": request.form.get("development_duration", "6 Weeks"),
        "required_technologies": request.form.get("required_technologies", "Python, React, AI/ML"),
        "ai_ml_requirement": request.form.get("ai_ml_requirement", "Yes"),
        "shortlist_count": request.form.get("shortlist_count", 5),
    }

    analyzer = ProblemAnalyzer()
    shortlisted = analyzer.analyze(project["rag_text"], team_profile, filters)
    if not shortlisted:
        return jsonify({
            "status": "error",
            "message": (
                "Could not identify problem statements in the extracted document text. "
                "Make sure the PDF is text-based (not a scanned image) and has problem titles, IDs, or descriptions."
            ),
        }), 422

    project["problem_statements"] = shortlisted
    project["selected_problem"] = {}
    project["solutions"] = []
    project["solutions_for_selection_key"] = ""
    project["selected_solution"] = {}
    project["tech_stack"] = {}
    project["pitch"] = {}
    project["team_profile"] = team_profile
    save_project_state(project)

    return jsonify({
        "status": "success",
        "message": "Problem analysis completed.",
        "problem_statements": shortlisted,
    })


@app.route("/api/generate-solutions", methods=["POST"])
def generate_solutions():
    project = ensure_project_state()
    selected_problem = project.get("selected_problem")
    if not selected_problem:
        return jsonify({"status": "error", "message": "Select a problem statement before generating solutions."}), 400

    generator = SolutionGenerator()
    try:
        solutions = generator.generate(
            selected_problem,
            project.get("team_profile", {}).get("team_skills", ""),
        )
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Could not generate solutions for the selected problem: {exc}",
        }), 502

    project["solutions"] = solutions
    project["solutions_for_selection_key"] = selected_problem.get("selection_key") or selected_problem.get("id", "")
    project["solution_generation_mode"] = generator.generation_mode
    project["selected_solution"] = {}
    project["tech_stack"] = {}
    project["pitch"] = {}
    save_project_state(project)

    return jsonify({
        "status": "success",
        "message": "Solution options generated for the selected problem statement.",
        "generation_mode": generator.generation_mode,
        "fallback_reason": generator.fallback_reason,
        "solutions": solutions,
    })


@app.route("/api/select-solution", methods=["POST"])
def select_solution():
    project = ensure_project_state()
    solution_name = request.form.get("solution_name")
    for item in project.get("solutions", []):
        if item.get("name") == solution_name:
            project["selected_solution"] = item
            project["tech_stack"] = {}
            project["pitch"] = {}
            break
    else:
        return jsonify({"status": "error", "message": "Valid solution selection is required."}), 400

    save_project_state(project)
    return jsonify({"status": "success", "message": "Solution selected.", "selected_solution": project["selected_solution"]})


@app.route("/api/generate-tech-stack", methods=["POST"])
def generate_tech_stack():
    project = ensure_project_state()
    if not project.get("selected_problem"):
        return jsonify({"status": "error", "message": "Select a problem statement first."}), 400

    selected_problem = project["selected_problem"]
    solutions = project.get("solutions") or [{}]
    selected_solution = project.get("selected_solution") or solutions[0]
    team_skills = request.form.get("team_skills", "Python, React, Machine Learning")
    duration = request.form.get("development_duration", "6 Weeks")
    required_features = request.form.get("required_features", "Dashboard, AI workflow, analytics")

    tech_stack = TechRecommender().recommend(selected_problem, selected_solution, team_skills, duration, required_features)
    project["tech_stack"] = tech_stack
    project["pitch"] = {}
    save_project_state(project)

    return jsonify({"status": "success", "message": "Technology stack generated.", "tech_stack": tech_stack})


@app.route("/api/select-problem", methods=["POST"])
def select_problem():
    project = ensure_project_state()
    selected_key = request.form.get("selection_key")
    selected_problem_id = request.form.get("problem_id")

    match = None
    for item in project.get("problem_statements", []):
        if (
            (selected_key and item.get("selection_key") == selected_key)
            or (selected_problem_id and item.get("id") == selected_problem_id)
        ):
            match = item
            break

    if not match:
        return jsonify({"status": "error", "message": "No valid problem statement was selected."}), 400

    project["selected_problem"] = match
    project["solutions"] = []
    project["solutions_for_selection_key"] = ""
    project["solution_generation_mode"] = ""
    project["selected_solution"] = {}
    project["tech_stack"] = {}
    project["pitch"] = {}
    save_project_state(project)
    return jsonify({
        "status": "success",
        "message": "Problem statement selected.",
        "selected_problem": match,
    })


@app.route("/api/generate-pitch", methods=["POST"])
def generate_pitch():
    project = ensure_project_state()
    if not project.get("selected_problem"):
        return jsonify({"status": "error", "message": "Generate project context before creating the pitch."}), 400

    try:
        pitch_duration = int(request.form.get("pitch_duration", 5))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Choose a pitch duration of 3, 5, or 10 minutes."}), 400
    if pitch_duration not in {3, 5, 10}:
        return jsonify({"status": "error", "message": "Choose a pitch duration of 3, 5, or 10 minutes."}), 400

    solutions = project.get("solutions") or [{}]
    try:
        pitch = PitchGenerator().generate(
            project["selected_problem"],
            project.get("selected_solution") or solutions[0],
            project.get("tech_stack", {}),
            pitch_duration,
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Could not generate the pitch deck: {exc}"}), 502
    if not isinstance(pitch, dict) or not isinstance(pitch.get("slides"), list) or not pitch["slides"]:
        return jsonify({"status": "error", "message": "Pitch generation returned no slides. Please try again."}), 502

    project["pitch"] = pitch
    save_project_state(project)

    return jsonify({"status": "success", "message": "Pitch deck generated.", "pitch": pitch})


@app.route("/api/chat", methods=["POST"])
def chat():
    project = ensure_project_state()
    question = request.form.get("message", "").strip()
    if not question:
        return jsonify({"status": "error", "message": "Please enter a question."}), 400

    recent_messages = project.get("chat_history", [])[-6:]
    selected_problem = project.get("selected_problem", {})
    source_fields = selected_problem.get("source_fields", {})
    problem_context = {
        "id": selected_problem.get("id") or source_fields.get("id"),
        "title": selected_problem.get("title") or source_fields.get("title"),
        "domain": selected_problem.get("domain") or source_fields.get("domain") or source_fields.get("theme"),
        "description": selected_problem.get("description") or source_fields.get("description"),
        "requirements": selected_problem.get("requirements") or source_fields.get("requirements"),
        "expected_outcome": selected_problem.get("expected_outcome") or source_fields.get("expected_outcome"),
        "constraints": selected_problem.get("constraints") or source_fields.get("constraints"),
    }
    context = {
        "problem": {key: value for key, value in problem_context.items() if value},
        "solution": {
            key: project.get("selected_solution", {}).get(key)
            for key in ("name", "overview", "core_functionality")
            if project.get("selected_solution", {}).get(key)
        },
        "technology_stack": project.get("tech_stack", {}),
    }

    prompt = (
        "You are a friendly hackathon mentor having a natural conversation with a student. "
        "Answer the latest question directly in plain text. Keep it simple and brief: normally 2-4 short sentences "
        "and under 80 words. Avoid markdown, headings, long plans, and jargon unless the user asks for detail. "
        "Use the project context and recent conversation when relevant. Never invent facts about the uploaded problem; "
        "say when something is not specified.\n\n"
        f"Project context: {context}\n"
        f"Recent conversation: {recent_messages}\n"
        f"Student: {question}\n"
        "Mentor:"
    )

    try:
        answer = GroqClient().chat(
            prompt,
            system_prompt="Be a warm, clear, concise conversational mentor. Reply in plain text.",
            temperature=0.4,
            max_tokens=250,
        ).strip()
        if not answer:
            raise RuntimeError("The AI returned an empty answer.")
    except Exception:
        answer = (
            "I can't reach the AI service right now. Please try again in a little while."
        )

    add_chat_message("user", question)
    add_chat_message("assistant", answer)
    project = ensure_project_state()
    return jsonify({"status": "success", "answer": answer, "history": project.get("chat_history", [])})


@app.route("/api/download-report")
def download_report():
    project = ensure_project_state()
    report = build_project_report(project)
    filepath = report_dir / "hackathon_report.txt"
    filepath.write_text(report, encoding="utf-8")
    return send_file(filepath, as_attachment=True, download_name="hackathon_report.txt", mimetype="text/plain")


@app.route("/api/clear-session")
def clear_session():
    project_id = session.pop("project_id", None)
    if project_id:
        project = project_store.load(project_id)
        if project:
            remove_stored_upload(project)
        project_store.delete(project_id)
    if app.vector_store is not None:
        app.vector_store.reset()
    return jsonify({"status": "success", "message": "Current project state was cleared."})


app.vector_store = None

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
