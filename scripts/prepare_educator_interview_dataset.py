from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.analysis import BatchAnalysisRequest  # noqa: E402
from app.services.analysis_service import AnalysisService  # noqa: E402


DOCX_PATH = ROOT_DIR / "教育家型教师访谈材料汇总.docx"
RAW_OUTPUT_PATH = ROOT_DIR / "data" / "raw" / "educator_interviews_raw.txt"
IMPORT_OUTPUT_PATH = ROOT_DIR / "data" / "samples" / "educator_interviews_import.csv"
ANALYSIS_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "educator_interviews_analysis.csv"
RULE_HIT_REVIEW_PATH = ROOT_DIR / "data" / "processed" / "educator_interviews_rule_hit_review.csv"
SUMMARY_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "educator_interviews_summary.json"

WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
PROFILE_HEADERS = {"编号", "姓名", "性别", "教龄", "教学科目"}
MIN_SEGMENT_LENGTH = 18
MAX_SEGMENT_LENGTH = 120


def normalize_whitespace(text: str) -> str:
    cleaned = (
        text.replace("\u3000", " ")
        .replace("\xa0", " ")
        .replace("\u200b", "")
        .replace("\ufeff", "")
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def extract_docx_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")

    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        text_nodes = paragraph.findall(".//w:t", WORD_NAMESPACE)
        content = normalize_whitespace("".join(node.text or "" for node in text_nodes))
        if content:
            paragraphs.append(content)
    return paragraphs


def parse_profiles(paragraphs: list[str]) -> dict[str, dict[str, str]]:
    try:
        start = paragraphs.index("访谈对象基本情况")
        end = paragraphs.index("访谈问题")
    except ValueError:
        return {}

    tokens = [item for item in paragraphs[start + 1:end] if item not in PROFILE_HEADERS]
    profiles: dict[str, dict[str, str]] = {}
    for index in range(0, len(tokens), 5):
        row = tokens[index:index + 5]
        if len(row) < 5:
            continue
        respondent_id, name, gender, teaching_years, subject = row
        if not re.fullmatch(r"A\d+", respondent_id):
            continue
        profiles[respondent_id] = {
            "respondent_name": name,
            "gender": gender,
            "teaching_years": teaching_years,
            "subject": subject,
        }
    return profiles


def parse_answers(paragraphs: list[str]) -> list[dict[str, str]]:
    try:
        start = paragraphs.index("访谈问题") + 1
    except ValueError:
        start = 0

    answers: list[dict[str, str]] = []
    current_question_id = ""
    current_question = ""
    last_answer: dict[str, str] | None = None

    for paragraph in paragraphs[start:]:
        question_match = re.match(r"^Q(\d+)[:：]\s*(.+)$", paragraph)
        if question_match:
            current_question_id = f"Q{question_match.group(1)}"
            current_question = question_match.group(2).strip()
            last_answer = None
            continue

        answer_match = re.match(r"^(A\d+)[:：]\s*(.+)$", paragraph)
        if answer_match:
            last_answer = {
                "question_id": current_question_id,
                "question": current_question,
                "respondent_id": answer_match.group(1),
                "answer_text": answer_match.group(2).strip(),
            }
            answers.append(last_answer)
            continue

        if last_answer is not None:
            last_answer["answer_text"] = normalize_whitespace(
                f"{last_answer['answer_text']} {paragraph}"
            )

    return answers


def split_long_piece(piece: str) -> list[str]:
    if len(piece) <= MAX_SEGMENT_LENGTH:
        return [piece]

    comma_parts = re.split(r"(?<=[，；：、])", piece)
    chunks: list[str] = []
    buffer = ""
    for part in comma_parts:
        part = part.strip()
        if not part:
            continue
        candidate = f"{buffer}{part}"
        if buffer and len(candidate) > MAX_SEGMENT_LENGTH:
            chunks.append(buffer.strip())
            buffer = part
        else:
            buffer = candidate
    if buffer.strip():
        chunks.append(buffer.strip())
    return chunks


def segment_answer_text(text: str) -> list[str]:
    sentence_like_parts = re.split(r"(?<=[。！？；])", text)
    prepared_parts: list[str] = []
    for part in sentence_like_parts:
        part = normalize_whitespace(part)
        if not part:
            continue
        prepared_parts.extend(split_long_piece(part))

    segments: list[str] = []
    buffer = ""
    for part in prepared_parts:
        candidate = f"{buffer} {part}".strip() if buffer else part
        if buffer and len(candidate) > MAX_SEGMENT_LENGTH:
            if len(buffer) >= MIN_SEGMENT_LENGTH:
                segments.append(buffer)
            buffer = part
            continue
        buffer = candidate

    if buffer and len(buffer) >= MIN_SEGMENT_LENGTH:
        segments.append(buffer)

    if not segments and len(text) >= MIN_SEGMENT_LENGTH:
        return [text[:MAX_SEGMENT_LENGTH].strip()]

    return segments


def build_dataset_rows(
    answers: list[dict[str, str]],
    profiles: dict[str, dict[str, str]],
    source_file: str,
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    segment_index = 1
    for answer in answers:
        respondent_id = answer["respondent_id"]
        profile = profiles.get(respondent_id, {})
        for text in segment_answer_text(answer["answer_text"]):
            rows.append(
                {
                    "segment_id": f"EDU-{segment_index:03d}",
                    "source_file": source_file,
                    "source_type": "educator_interview",
                    "data_role": "campus_domain_reference",
                    "question_id": answer["question_id"],
                    "question": answer["question"],
                    "respondent_id": respondent_id,
                    "respondent_name": profile.get("respondent_name", ""),
                    "gender": profile.get("gender", ""),
                    "teaching_years": profile.get("teaching_years", ""),
                    "subject": profile.get("subject", ""),
                    "text": text,
                    "text_length": len(text),
                }
            )
            segment_index += 1
    return rows


def run_analysis(
    rows: list[dict[str, str | int]],
) -> tuple[list[dict[str, str | int | float | bool]], dict[str, object]]:
    texts = [str(row["text"]) for row in rows]
    service = AnalysisService()
    response = service.analyze_batch(BatchAnalysisRequest(texts=texts))

    analyzed_rows: list[dict[str, str | int | float | bool]] = []
    for row, result in zip(rows, response.results, strict=True):
        analyzed_rows.append(
            {
                **row,
                "category": result.category,
                "level": result.level,
                "score": result.score,
                "score_breakdown": json.dumps(
                    [factor.model_dump() for factor in result.score_breakdown],
                    ensure_ascii=False,
                ),
                "keywords": "|".join(result.keywords),
                "rule_reason": result.rule_reason,
                "llm_explanation": result.llm_explanation,
                "needs_attention": result.needs_attention,
            }
        )

    summary = {
        "source_file": DOCX_PATH.name,
        "paragraph_count": len(extract_docx_paragraphs(DOCX_PATH)),
        "answer_count": len({(row["question_id"], row["respondent_id"]) for row in rows}),
        "segment_count": len(rows),
        "category_distribution": response.summary.category_distribution,
        "level_distribution": response.summary.level_distribution,
        "attention_count": response.summary.attention_count,
        "top_keywords": [
            {"keyword": item.keyword, "count": item.count}
            for item in response.summary.top_keywords
        ],
        "wordcloud_keywords": [
            {"keyword": item.keyword, "count": item.count}
            for item in response.summary.wordcloud_keywords
        ],
        "question_distribution": dict(Counter(str(row["question_id"]) for row in rows)),
    }
    return analyzed_rows, summary


def write_raw_text(paragraphs: Iterable[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(paragraphs), encoding="utf-8")


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not DOCX_PATH.exists():
        raise FileNotFoundError(f"Source document not found: {DOCX_PATH}")

    paragraphs = extract_docx_paragraphs(DOCX_PATH)
    profiles = parse_profiles(paragraphs)
    answers = parse_answers(paragraphs)
    rows = build_dataset_rows(answers, profiles, DOCX_PATH.name)
    analyzed_rows, summary = run_analysis(rows)
    rule_hit_rows = [row for row in analyzed_rows if row["keywords"] or row["needs_attention"]]

    write_raw_text(paragraphs, RAW_OUTPUT_PATH)
    write_csv(rows, IMPORT_OUTPUT_PATH)
    write_csv(analyzed_rows, ANALYSIS_OUTPUT_PATH)
    write_csv(rule_hit_rows, RULE_HIT_REVIEW_PATH)
    write_json(summary, SUMMARY_OUTPUT_PATH)

    print(f"Source file: {DOCX_PATH.name}")
    print(f"Profiles parsed: {len(profiles)}")
    print(f"Answer records: {len(answers)}")
    print(f"Dataset segments: {len(rows)}")
    print(f"Category distribution: {summary['category_distribution']}")
    print(f"Level distribution: {summary['level_distribution']}")
    print("Outputs:")
    print(f"  - {RAW_OUTPUT_PATH}")
    print(f"  - {IMPORT_OUTPUT_PATH}")
    print(f"  - {ANALYSIS_OUTPUT_PATH}")
    print(f"  - {RULE_HIT_REVIEW_PATH}")
    print(f"  - {SUMMARY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
