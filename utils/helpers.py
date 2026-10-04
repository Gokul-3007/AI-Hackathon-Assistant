import json
import re
from typing import Any


def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned.strip()


def parse_json(response_text: str) -> Any:
    text = response_text.strip().lstrip("\ufeff")
    if not text:
        return {}

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character not in "{[":
            continue
        try:
            payload, _end = decoder.raw_decode(text[index:])
            if isinstance(payload, (dict, list)):
                return payload
        except json.JSONDecodeError:
            continue
    return {}


def build_project_report(project: dict) -> str:
    selected_problem = project.get("selected_problem", {})
    selected_solution = project.get("selected_solution", {})
    tech_stack = project.get("tech_stack", {})
    pitch = project.get("pitch", {})

    lines = [
        "AI HACKATHON ASSISTANT REPORT",
        "=" * 40,
        "\n1. Selected Problem Statement",
    ]
    if selected_problem:
        lines.append(f"ID: {selected_problem.get('id', 'N/A')}")
        lines.append(f"Title: {selected_problem.get('title', 'N/A')}")
        lines.append(f"Compatibility: {selected_problem.get('compatibility', 'N/A')}")
        lines.append(f"Reasoning: {selected_problem.get('reasoning', 'N/A')}")
    else:
        lines.append("No problem selected yet.")

    lines.extend([
        "\n2. Problem Analysis",
        f"Technical Feasibility: {selected_problem.get('technical_feasibility', 'N/A')}",
        f"AI/ML Scope: {selected_problem.get('ai_scope', 'N/A')}",
        f"Prototype Feasibility: {selected_problem.get('prototype_feasibility', 'N/A')}",
        f"Innovation: {selected_problem.get('innovation_opportunities', 'N/A')}",
        "\n3. Proposed Solution",
        selected_solution.get("name", "N/A"),
        selected_solution.get("overview", "N/A"),
        "\n4. Technology Stack",
    ])

    tech_data = tech_stack.get("technology_recommendations", {})
    if tech_data:
        for key, value in tech_data.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("No technology stack generated yet.")

    lines.extend([
        "\n5. Pitch Summary",
        pitch.get("project_name", "N/A"),
        pitch.get("tagline", "N/A"),
    ])

    slide_count = len(pitch.get("slides", []))
    lines.append(f"Slides generated: {slide_count}")
    return "\n".join(lines)
