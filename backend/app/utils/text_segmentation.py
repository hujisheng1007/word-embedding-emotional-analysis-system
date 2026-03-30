from __future__ import annotations

import re


SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？；!?])")
CLAUSE_SPLIT_PATTERN = re.compile(r"(?<=[，、；：,])")


def split_text_for_analysis(
    text: str,
    *,
    target_length: int = 220,
    max_length: int = 320,
    min_length: int = 60,
) -> list[str]:
    normalized = text.replace("\r", "\n")
    paragraphs = [item.strip() for item in re.split(r"\n{2,}|\n", normalized) if item.strip()]
    if not paragraphs:
        return []

    prepared_units: list[str] = []
    for paragraph in paragraphs:
        sentences = [item.strip() for item in SENTENCE_SPLIT_PATTERN.split(paragraph) if item.strip()]
        if not sentences:
            continue
        for sentence in sentences:
            if len(sentence) <= max_length:
                prepared_units.append(sentence)
                continue
            clauses = [item.strip() for item in CLAUSE_SPLIT_PATTERN.split(sentence) if item.strip()]
            buffer = ""
            for clause in clauses:
                candidate = f"{buffer}{clause}"
                if buffer and len(candidate) > max_length:
                    prepared_units.append(buffer.strip())
                    buffer = clause
                else:
                    buffer = candidate
            if buffer.strip():
                prepared_units.append(buffer.strip())

    if not prepared_units:
        cleaned = " ".join(text.split()).strip()
        return [cleaned] if cleaned else []

    segments: list[str] = []
    buffer = ""
    for unit in prepared_units:
        candidate = f"{buffer} {unit}".strip() if buffer else unit
        if buffer and len(candidate) > target_length:
            if len(buffer) >= min_length or not segments:
                segments.append(buffer.strip())
                buffer = unit
            else:
                buffer = candidate
        else:
            buffer = candidate

    if buffer.strip():
        if len(buffer) < min_length and segments:
            segments[-1] = f"{segments[-1]} {buffer}".strip()
        else:
            segments.append(buffer.strip())

    return [segment for segment in segments if segment]
