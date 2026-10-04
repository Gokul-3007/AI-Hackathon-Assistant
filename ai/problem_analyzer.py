import re


FIELD_PATTERNS = {
    "id": r"(?:problem\s*statement\s*)?(?:id|number|no\.?)",
    "title": r"(?:problem\s*statement\s*)?title",
    "track": r"(?:track|type|format)",
    "organization": r"(?:organization|organisation|department|agency|company|institution)",
    "domain": r"(?:domain|sector|category)",
    "theme": r"theme",
    "description": r"(?:problem\s*statement|description|background|overview)",
    "requirements": r"(?:functional\s*)?requirements?",
    "expected_outcome": r"(?:expected\s*)?(?:outcome|deliverables?|results?)",
    "constraints": r"(?:constraints?|limitations?)",
    "additional_information": r"(?:additional\s*information|other\s*information|notes?)",
}

FIELD_LABEL = re.compile(
    r"(?im)(?:^|\n)\s*(?P<label>"
    + "|".join(f"(?:{pattern})" for pattern in FIELD_PATTERNS.values())
    + r")\s*[:\-–]?\s*"
)
DOMAIN_ALIASES = {
    "healthcare": ("health", "medical", "medtech", "biotech", "healthtech"),
    "agriculture": ("agriculture", "agritech", "foodtech", "rural development"),
    "education": ("education", "edtech", "smart education"),
    "finance": ("finance", "financial", "fintech", "banking"),
}
ID_VALUE = re.compile(r"^[\s:#-]*([A-Z]{0,8}[-\s]?\d[A-Z0-9-]{2,})", re.I)
PROBLEM_ID = re.compile(
    r"(?im)^\s*(?:problem\s*statement\s*(?:id|number|no\.?)|"
    r"(?:PS|SIH)\s*[-#]?\s*\d{3,})\s*[:\-]?\s*"
)


def _normalize_document(text):
    text = text.replace("\x00", "").replace("\f", "\n")
    text = text.replace("\u00a0", " ").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*\n+", "\n", text)
    return text.strip()


def _field_name(label):
    normalized = re.sub(r"[^a-z]", "", label.lower())
    for name, pattern in FIELD_PATTERNS.items():
        if re.fullmatch(pattern, label.strip(), flags=re.I):
            return name
    if normalized in {"problemtitle", "title"}:
        return "title"
    if normalized in {"problemstatement", "description", "background", "overview"}:
        return "description"
    return None


def _extract_fields(block):
    matches = list(FIELD_LABEL.finditer(block))
    fields = {}
    for index, match in enumerate(matches):
        key = _field_name(match.group("label"))
        if not key:
            continue

        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        value = block[match.end():end].strip(" \t\r\n:;-")
        if key == "id":
            id_match = ID_VALUE.search(value)
            value = id_match.group(1).strip() if id_match else value.splitlines()[0].strip() if value else ""
        else:
            value = re.sub(r"\s+", " ", value).strip()

        if value and key not in fields:
            fields[key] = value

    if "id" not in fields:
        id_match = re.search(r"\b(?:PS|SIH)\s*[-#]?\s*\d{3,}\b", block, re.I)
        if id_match:
            fields["id"] = re.sub(r"\s+", "", id_match.group(0)).upper()
    return fields


class ProblemAnalyzer:
    def __init__(self, client=None):
        # Problem facts are parsed from the source document, never rewritten by an LLM.
        self.client = client

    def extract_candidates(self, text):
        normalized = _normalize_document(text or "")
        if not normalized:
            return []

        anchors = list(PROBLEM_ID.finditer(normalized))
        if len(anchors) < 2:
            title_anchors = list(
                re.finditer(
                    r"(?im)^\s*(?:problem\s*statement\s*)?title\s*[:\-–]?\s*",
                    normalized,
                )
            )
            if len(title_anchors) > 1:
                anchors = title_anchors

        blocks = []
        if len(anchors) > 1:
            for index, anchor in enumerate(anchors):
                end = anchors[index + 1].start() if index + 1 < len(anchors) else len(normalized)
                block = normalized[anchor.start():end].strip()
                if block:
                    blocks.append(block)
        else:
            blocks = [normalized]

        candidates = []
        seen = set()
        for block in blocks:
            fields = _extract_fields(block)
            if not any(key in fields for key in ("title", "description", "requirements")):
                continue
            identity = (fields.get("id", ""), fields.get("title", ""), fields.get("description", ""))
            if identity not in seen:
                candidates.append({"fields": fields, "source_text": block})
                seen.add(identity)
        return candidates

    def _score_candidate(self, candidate, team_profile, filters):
        fields = candidate["fields"]
        source = candidate["source_text"].casefold()
        score = 50
        reasons = []

        preferred_domain = (filters.get("preferred_domain") or "").strip()
        if preferred_domain:
            document_domain = (fields.get("domain") or fields.get("theme") or "").casefold()
            aliases = DOMAIN_ALIASES.get(preferred_domain.casefold(), (preferred_domain.casefold(),))
            matched_domain = next((alias for alias in aliases if alias in document_domain), "")
            if matched_domain:
                score += 20
                reasons.append(
                    f"document domain matches preferred domain ({fields.get('domain') or fields.get('theme')})"
                )
            else:
                score -= 10
                reasons.append(f"document domain does not match preferred domain ({preferred_domain})")

        skills = [
            skill.strip().casefold()
            for skill in re.split(r"[,;\n]", team_profile.get("team_skills", ""))
            if skill.strip()
        ]
        matched_skills = [skill for skill in skills if skill in source]
        if matched_skills:
            score += min(15, 5 * len(matched_skills))
            reasons.append(f"source text mentions team skills: {', '.join(matched_skills)}")
        elif skills:
            reasons.append("no entered team skill is explicitly mentioned in the source text")

        ai_required = filters.get("ai_ml_requirement") == "Yes"
        ai_evidence = re.search(r"\b(ai|artificial intelligence|machine learning|ml|deep learning)\b", source)
        if ai_required:
            if ai_evidence:
                score += 10
                reasons.append("source text explicitly mentions AI/ML")
            else:
                reasons.append("source text does not explicitly mention AI/ML")

        score = max(0, min(100, score))
        compatibility = "High" if score >= 75 else "Medium" if score >= 55 else "Low"
        return score, compatibility, reasons

    def analyze(self, source_text, team_profile, filters):
        candidates = self.extract_candidates(source_text)
        if not candidates:
            return []

        result = []
        for index, candidate in enumerate(candidates, start=1):
            fields = candidate["fields"]
            score, compatibility, reasons = self._score_candidate(candidate, team_profile, filters)
            source_description = " ".join(
                [
                    candidate["source_text"],
                    fields.get("description", ""),
                    fields.get("requirements", ""),
                    fields.get("expected_outcome", ""),
                    fields.get("constraints", ""),
                ]
            ).casefold()

            result.append({
                "id": fields.get("id", ""),
                "selection_key": fields.get("id") or f"statement-{index}",
                "title": fields.get("title", ""),
                "domain": fields.get("domain") or fields.get("theme", ""),
                "organization": fields.get("organization", ""),
                "description": fields.get("description", ""),
                "requirements": fields.get("requirements", ""),
                "expected_outcome": fields.get("expected_outcome", ""),
                "constraints": fields.get("constraints", ""),
                "additional_information": fields.get("additional_information", ""),
                "source_fields": fields,
                "compatibility": compatibility,
                "score": score,
                "reasoning": "; ".join(reasons) if reasons else "No team-fit filters were provided; score is neutral.",
                "technical_feasibility": "Not stated in source",
                "ai_scope": "Mentioned in source" if re.search(r"\b(ai|artificial intelligence|machine learning|ml|deep learning)\b", source_description) else "Not stated in source",
                "prototype_feasibility": "Not stated in source",
                "innovation_opportunities": "Requires team review",
                "development_complexity": "Not stated in source",
                "required_skills": [],
                "potential_challenges": [],
                "possible_innovation": [],
                "source_excerpt": candidate["source_text"],
            })

        result.sort(key=lambda item: item["score"], reverse=True)
        try:
            shortlist_count = int(filters.get("shortlist_count", 5))
        except (TypeError, ValueError):
            shortlist_count = 5
        return result[:max(1, min(shortlist_count, 50))]
