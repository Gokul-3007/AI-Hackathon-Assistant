# AI Hackathon Assistant

A complete Flask-based AI dashboard for hackathon preparation. The app helps users upload problem statements, shortlist project ideas, generate technical solutions, recommend a stack, and prepare a pitch deck using RAG and Groq-powered LLM responses.

## Features

- Upload PDF, DOCX, or TXT problem statement documents
- Extract, clean, and chunk text for retrieval-augmented generation
- Build a local vector store for contextual document retrieval
- Rank and shortlist hackathon problem statements using team profile and filters
- Display extracted problem IDs, titles, tracks, domains, organizations, and any other labeled source fields without asking the LLM to rewrite source facts
- Generate multiple solution options tied to the selected problem
- Recommend a technology stack and architecture
- Create a pitch deck with slide scripts
- Chat with the AI mentor about the current project context
- Use a simple chat UI with suggested questions and short, plain-language answers
- Download a generated report

## Project structure

- `app.py` — Flask application entry point
- `data/projects.sqlite3` — server-side project/session data store (created automatically)
- `templates/index.html` — main dashboard UI
- `static/css/style.css` — responsive UI styling
- `static/js/script.js` — frontend interactions and API calls
- `rag/` — chunking, embeddings, and vector-store logic
- `ai/` — Groq integration and generation modules
- `data/sample_problem_statements.txt` — sample project input
- `uploads/` — uploaded documents
- `.env.example` — environment variable template

## Installation

1. Create and activate a Python virtual environment if needed.
2. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and update the values:

   ```bash
   cp .env.example .env
   ```

4. Set your Groq API key in `.env`:

   ```env
   GROQ_API_KEY=your_api_key_here
   GROQ_MODEL=qwen/qwen3.8-27b
   SECRET_KEY=change-me
   ```

   A local `.env` file has been created for the provided Groq key and is used by the backend.

## Running the app

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Usage flow

1. Upload a document containing hackathon problem statements.
2. Set preferred domain, team skills, and shortlist requirements.
3. Analyze the shortlist and select the best-fit problem.
4. Generate solution options.
5. Select the most suitable solution.
6. Generate the technology stack and architecture.
7. Generate the pitch deck.
8. Chat with the AI mentor and download the final report.

## Notes

- Groq API calls are processed server-side only.
- `GROQ_MODEL` selects the active Groq chat model; defaults to `qwen/qwen3.8-27b`.
- Project state and extracted document text are stored server-side in SQLite; the browser cookie contains only a small project identifier, avoiding cookie-size loss after upload.
- Opening the app starts a fresh project, so upload the problem document again for each new visit; the previous visit's project and tracked uploaded file are cleared.
- Uploads are limited to 20 MB and support PDF, DOCX, and TXT files.
- Upload bytes are validated and parsed directly before saving, and every new upload clears the previous document's analysis so errors cannot leave stale results on screen.
- Scanned/image-only PDFs are not OCR-processed. A PDF table index is reconstructed from its text positions; missing fields are left unstated instead of being invented.
- Solution generation reports Groq/API failures instead of displaying generic sample solutions as if they were generated for the selected problem.
- Solution generation uses only the selected problem statement, not document-wide retrieval context. If Groq is blocked by quota/rate limits or a temporary network/DNS failure, it reports the problem and shows no generic substitute solutions.
- For local development, the RAG implementation uses a lightweight in-memory TF-IDF vector store, avoiding large model downloads during document upload.
