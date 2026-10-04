from bisect import bisect_right
from io import BytesIO
import re
from pathlib import Path

from docx import Document
from PyPDF2 import PdfReader


def _extract_problem_index(page_spans, extracted_text):
    if not re.search(r"PS\s*CODE.*PROBLEM\s*STATEMENT\s*TITLE", extracted_text, re.I | re.S):
        return ""
    if len(re.findall(r"\bSIH\s*\d{5}\b", extracted_text, re.I)) < 2:
        return ""

    records = []
    for spans in page_spans:
        code_spans = [
            span for span in spans
            if re.search(r"\bSIH\s*\d{5}\b", span[2], re.I)
        ]
        code_spans.sort(key=lambda span: span[0])
        if not code_spans:
            continue

        row_starts = [span[0] - 2 for span in code_spans]
        row_fields = [
            {
                "id": re.sub(
                    r"\s+",
                    "",
                    re.search(r"SIH\s*\d{5}", code_span[2], re.I).group(0),
                ).upper(),
                "track": [],
                "title": [],
                "domain": [],
                "organization": [],
            }
            for code_span in code_spans
        ]
        for y, x, value in spans:
            row_index = bisect_right(row_starts, y) - 1
            if row_index < 0:
                continue
            if row_index + 1 < len(code_spans) and y >= code_spans[row_index + 1][0] - 2:
                continue
            if row_index + 1 == len(code_spans) and y >= code_spans[row_index][0] + 200:
                continue
            if re.search(r"Smart India Hackathon|BlinkNBuild|Page\s+\d+\s+of\s+\d+", value, re.I):
                continue
            if x < 150 or re.search(r"\bSIH\s*\d{5}\b", value, re.I):
                continue

            columns = row_fields[row_index]
            if value.upper() in {"SOFTWARE", "HARDWARE"}:
                columns["track"].append((y, x, value))
            elif x < 485:
                columns["title"].append((y, x, value))
            elif x < 580:
                columns["domain"].append((y, x, value))
            else:
                columns["organization"].append((y, x, value))

        for columns in row_fields:
            fields = {"id": columns["id"]}
            for name in ("track", "title", "domain", "organization"):
                values = columns[name]
                if values:
                    content = " ".join(value for _y, _x, value in sorted(values))
                    content = re.sub(r"\s+([,.;:!?%)])", r"\1", content)
                    content = re.sub(r"([(])\s+", r"\1", content)
                    content = re.sub(r"\s+-\s+", "-", content)
                    fields[name] = re.sub(r"\s+", " ", content).strip()

            if fields.get("title"):
                records.append(fields)

    if len(records) < 2:
        return ""

    formatted = []
    for fields in records:
        formatted.extend([
            f"Problem Statement ID: {fields['id']}",
            f"Title: {fields.get('title', '')}",
            f"Track: {fields.get('track', '')}",
            f"Theme: {fields.get('domain', '')}",
            f"Organization: {fields.get('organization', '')}",
        ])
    return "\n".join(formatted)


def extract_text_from_bytes(contents, suffix):
    suffix = suffix.lower()
    if not contents:
        raise ValueError("The uploaded file contains no data.")
    if suffix == ".txt":
        return contents.decode("utf-8-sig", errors="replace")

    if suffix == ".pdf":
        if not contents.startswith(b"%PDF-"):
            raise ValueError("This file is not a valid PDF. Please select the original PDF document.")
        reader = PdfReader(BytesIO(contents), strict=False)
        texts = []
        page_spans = []
        for page in reader.pages:
            spans = []

            def collect_span(text, _cm, tm, _font, _font_size):
                value = text.strip()
                if value:
                    spans.append((float(tm[5]), float(tm[4]), value))

            texts.append(page.extract_text(visitor_text=collect_span) or "")
            page_spans.append(spans)
        extracted_text = "\n".join(texts)
        indexed_problems = _extract_problem_index(page_spans, extracted_text)
        return indexed_problems or extracted_text

    if suffix in {".doc", ".docx"}:
        if suffix == ".doc":
            raise ValueError("Legacy .doc files are not supported. Please save the document as .docx or PDF.")
        doc = Document(BytesIO(contents))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    raise ValueError(f"Unsupported file type: {suffix}")


def extract_text_from_file(file_path):
    path = Path(file_path)
    return extract_text_from_bytes(path.read_bytes(), path.suffix)


def list_uploaded_documents(upload_dir):
    upload_path = Path(upload_dir)
    if not upload_path.exists():
        return []

    docs = []
    for item in sorted(upload_path.iterdir()):
        if item.is_file():
            docs.append({
                "name": item.name,
                "path": str(item),
                "size": item.stat().st_size,
            })
    return docs
