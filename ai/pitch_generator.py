import json

from ai.groq_client import GroqClient
from utils.helpers import parse_json


class PitchGenerator:
    def __init__(self, client=None):
        self.client = client or GroqClient()

    def generate(self, problem_statement, selected_solution, tech_stack, pitch_duration=5):
        prompt = (
            "You are a hackathon pitch coach. Generate a concise but professional pitch deck for this project. "
            "Return valid JSON only with keys: project_name, tagline, slides, pitch_script. Each slide must contain: title, content, script. "
            "The slide count should be between 8 and 12 and fit a roughly 5 minute pitch. "
            f"Problem statement: {json.dumps(problem_statement, indent=2)}\n"
            f"Selected solution: {json.dumps(selected_solution, indent=2)}\n"
            f"Technology stack: {json.dumps(tech_stack, indent=2)}\n"
            f"Pitch duration in minutes: {pitch_duration}"
        )

        try:
            response = self.client.chat(prompt, system_prompt="Return valid JSON only.")
            payload = parse_json(response)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        slides = [
            {"title": "Title", "content": "AI-powered solution for a real world challenge.", "script": "Good morning everyone. Today we are presenting a solution designed to tackle a critical real-world problem."},
            {"title": "Problem Statement", "content": "Users struggle with inefficient workflows, poor visibility, and slow decision-making.", "script": "The problem we identified is a recurring issue that affects speed, efficiency, and outcomes."},
            {"title": "Existing Challenges", "content": "Current approaches are manual, inconsistent, and limited in scalability.", "script": "Most existing solutions rely on slow manual steps and do not adapt quickly to real-world complexity."},
            {"title": "Proposed Solution", "content": "An AI-assisted platform that combines retrieval, prediction, and recommendations.", "script": "Our solution addresses this by combining AI, relevant data, and a simplified interface."},
            {"title": "Key Features", "content": "Smart analysis, real-time insights, role-based dashboards, and actionable recommendations.", "script": "The product provides a clear workflow from data ingestion to action-oriented output."},
            {"title": "How It Works", "content": "Input -> Retrieval -> AI reasoning -> Output -> Decision support.", "script": "Users begin with simple input, the system retrieves context, and AI generates useful recommendations."},
            {"title": "Technology Stack", "content": "Python, Flask, React, Groq, Machine Learning, and cloud hosting.", "script": "The technology stack balances speed, flexibility, and hackathon feasibility."},
            {"title": "System Architecture", "content": "Frontend, Flask API, vector store, model inference, and data persistence.", "script": "Our architecture is modular, easy to scale, and supports iterative development."},
            {"title": "Innovation", "content": "We use contextual retrieval and AI workflow optimization to improve practical impact.", "script": "What differentiates our product is the integration of retrieval-aware AI with a user-centered workflow."},
            {"title": "Impact", "content": "Faster decisions, improved outcomes, lower friction, and measurable value for users.", "script": "This solution can create meaningful impact across time, cost, and accessibility."},
            {"title": "Future Scope", "content": "Expand to analytics, personalization, multi-user deployment, and more data sources.", "script": "In the future, we can extend the platform with broader integrations and stronger production readiness."},
            {"title": "Conclusion", "content": "We have built a practical and impactful hackathon-ready solution with clear business value.", "script": "In summary, our project tackles a real pain point with a scalable and innovative approach."},
        ]

        return {
            "project_name": problem_statement.get("title", "AI Hackathon Solution").replace("AI-", "").strip(),
            "tagline": "Building smarter decisions with contextual AI.",
            "slides": slides,
            "pitch_script": "\n\n".join([f"Slide {index + 1}: {slide['title']}\n{slide['script']}" for index, slide in enumerate(slides)]),
        }
