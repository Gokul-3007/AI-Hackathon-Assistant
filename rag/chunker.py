import re


def chunk_text(text, chunk_size=500, overlap=100):
    if not text or not text.strip():
        return []

    normalized = re.sub(r"\s+", " ", text).strip()
    paragraphs = re.split(r"(?=Problem Statement ID:|PS-\d+|Title:|Description:|Requirements:)", normalized)
    cleaned = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current = ""
    for paragraph in cleaned:
        if len(current) + len(paragraph) <= chunk_size:
            current = (current + " " + paragraph).strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    if not chunks:
        words = normalized.split()
        chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), max(1, chunk_size - overlap)) if i < len(words)]

    return chunks
