import json

from ai.groq_client import GroqClient
from utils.helpers import parse_json


class TechRecommender:
    def __init__(self, client=None):
        self.client = client or GroqClient()

    def recommend(self, problem_statement, selected_solution, team_skills, duration, required_features):
        prompt = (
            "You are a senior software architect. Recommend a complete technology stack for a hackathon prototype. "
            "Return valid JSON only with keys: frontend, backend, ai_ml, database, deployment, architecture, recommendations, "
            "database_requirements, api_requirements, external_api_requirements, ai_model_requirements, deployment_requirements, "
            "security_considerations, scalability_considerations.\n\n"
            f"Problem statement: {json.dumps(problem_statement, indent=2)}\n"
            f"Selected solution: {json.dumps(selected_solution, indent=2)}\n"
            f"Team skills: {team_skills}\n"
            f"Development duration: {duration}\n"
            f"Required features: {required_features}"
        )

        try:
            response = self.client.chat(prompt, system_prompt="Return valid JSON only.")
            payload = parse_json(response)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        return {
            "frontend": [
                {"Technology": "React", "Why": "Fast UI development and component reuse for dashboards and forms.", "Alternative": "Next.js", "Difficulty": "Medium", "Purpose": "User interface"},
                {"Technology": "Tailwind CSS", "Why": "Rapid UI styling and polished responsive design.", "Alternative": "Bootstrap", "Difficulty": "Easy", "Purpose": "Styling"},
            ],
            "backend": [
                {"Technology": "Flask", "Why": "Lightweight Python backend ideal for AI-focused prototypes.", "Alternative": "FastAPI", "Difficulty": "Medium", "Purpose": "API and service layer"},
                {"Technology": "Python", "Why": "Strong ecosystem for AI, data processing, and model integration.", "Alternative": "Node.js", "Difficulty": "Easy", "Purpose": "Core application logic"},
            ],
            "ai_ml": [
                {"Technology": "Scikit-learn", "Why": "Useful for tabular models, clustering, and baseline ML prototypes.", "Alternative": "XGBoost", "Difficulty": "Medium", "Purpose": "Machine learning"},
                {"Technology": "PyTorch", "Why": "Flexible model development for advanced AI pipelines.", "Alternative": "TensorFlow", "Difficulty": "Medium", "Purpose": "Deep learning"},
            ],
            "database": [
                {"Technology": "MongoDB", "Why": "Flexible document storage for fast prototype iterations.", "Alternative": "PostgreSQL", "Difficulty": "Medium", "Purpose": "Data persistence"},
            ],
            "deployment": [
                {"Technology": "Render", "Why": "Simple deployment workflow for web apps and APIs.", "Alternative": "Vercel", "Difficulty": "Easy", "Purpose": "Hosting"},
            ],
            "architecture": "Frontend -> Flask API -> RAG + model inference -> database and analytics layer.",
            "recommendations": [
                "Use Flask or FastAPI for a lean API layer.",
                "Add a local vector store for document retrieval and contextual AI generation.",
                "Keep the prototype modular so it can evolve into a real product.",
            ],
            "database_requirements": ["User profiles", "Prediction history", "Session data", "Model metadata"],
            "api_requirements": ["Authentication endpoints", "Upload and retrieval endpoints", "Prediction execution API"],
            "external_api_requirements": ["Groq API for LLM inference", "Optional cloud storage or analytics service"],
            "ai_model_requirements": ["Classification or recommendation model", "Model evaluation metrics", "Monitoring and logging"],
            "deployment_requirements": ["Secure environment variables", "Production-ready API keys", "Deployment pipeline"],
            "security_considerations": ["Protect API keys", "Sanitize uploaded files", "Encrypt sensitive data"],
            "scalability_considerations": ["Use async tasks for heavy inference", "Add caching for repeated requests", "Separate services for analytics and inference"],
        }
