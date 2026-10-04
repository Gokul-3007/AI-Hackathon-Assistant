import requests

from ai.groq_client import GroqClient
from utils.helpers import parse_json


class SolutionGenerator:
    def __init__(self, client=None):
        self.client = client or GroqClient()
        self.generation_mode = "groq"
        self.fallback_reason = ""

    def generate(self, problem_statement, team_skills):
        source_fields = problem_statement.get("source_fields", {})
        source_details = problem_statement.get("source_excerpt") or "\n".join(
            f"{key}: {value}"
            for key, value in source_fields.items()
            if value
        )
        source_title = source_fields.get("title") or problem_statement.get("title") or ""
        source_id = source_fields.get("id") or problem_statement.get("id") or ""
        source_requirements = "\n".join(
            str(source_fields.get(key, ""))
            for key in ("description", "problem_statement", "requirements", "expected_outcome", "constraints")
            if source_fields.get(key)
        ) or source_details
        prompt = (
            "You are a senior solution architect. Generate 3 distinct, practical solution options for ONLY the single selected "
            "problem statement below. The uploaded document may contain other challenges; ignore all of them. Do not substitute "
            "a generic dashboard, workflow, or monitoring app unless that directly addresses this statement. Derive each option's "
            "core functionality from the selected statement. Do not invent source requirements; clearly label any added design "
            "choices as proposed implementation details. If the selected statement lacks enough detail, say what is missing "
            "instead of guessing. For source_requirement_addressed, include an exact short quote copied from the selected statement. "
            "Return valid JSON only, with a key named 'solutions' whose value is an array of objects. Each object must contain: "
            "name, overview, source_requirement_addressed, target_users, core_functionality, required_technologies, ai_ml_components, advantages, "
            "limitations, innovation_opportunities, development_complexity, prototype_requirements, future_scalability.\n\n"
            f"Selected problem ID: {source_id}\n"
            f"Selected problem title: {source_title}\n"
            f"Selected problem statement, the only authoritative challenge context:\n{source_details}\n"
            f"Team skills (use only to choose feasible technologies): {team_skills}"
        )

        system_prompt = "Return valid JSON only. Do not include Markdown fences or explanation outside the JSON."
        try:
            response = self.client.chat(
                prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=4096,
                json_mode=True,
            )
        except (RuntimeError, requests.exceptions.RequestException) as exc:
            message = str(exc)
            lowered = message.casefold()
            if not any(
                term in lowered
                for term in (
                    "rate limit",
                    "quota",
                    "429",
                    "connect",
                    "connection",
                    "network",
                    "dns",
                    "resolve",
                    "timed out",
                    "timeout",
                )
            ):
                raise
            raise RuntimeError(
                f"{message} No solutions were shown, to avoid suggesting ideas that may not match the selected problem. "
                "Please retry when Groq is available."
            ) from exc

        payload = parse_json(response)
        if isinstance(payload, list):
            solution_items = payload
        elif isinstance(payload, dict):
            solution_items = next(
                (
                    value
                    for key, value in payload.items()
                    if key.casefold() in {"solutions", "solution_options", "proposed_solutions"}
                    and isinstance(value, list)
                ),
                [],
            )
        else:
            solution_items = []

        normalized_solutions = []
        for item in solution_items:
            if not isinstance(item, dict):
                continue
            normalized = {
                str(key).strip().lower().replace(" ", "_"): value
                for key, value in item.items()
            }
            if not normalized.get("name"):
                normalized["name"] = normalized.get("solution_name") or normalized.get("title")
            if not normalized.get("overview"):
                normalized["overview"] = normalized.get("solution_overview") or normalized.get("description")
            source_quote = normalized.get("source_requirement_addressed")
            if (
                normalized.get("name")
                and normalized.get("overview")
                and normalized.get("core_functionality")
                and isinstance(source_quote, str)
                and self._quote_is_from_source(source_quote, source_requirements)
            ):
                normalized_solutions.append(normalized)

        if not normalized_solutions:
            raise ValueError(
                "The AI did not return a solution that could be verified against the selected problem statement. "
                "No unrelated solutions were shown; please retry."
            )
        return normalized_solutions[:5]

    @staticmethod
    def _quote_is_from_source(quote, source_details):
        def normalize(value):
            return " ".join(value.split()).casefold()

        normalized_quote = normalize(quote.strip("\"'“”‘’"))
        return bool(normalized_quote) and normalized_quote in normalize(source_details)
