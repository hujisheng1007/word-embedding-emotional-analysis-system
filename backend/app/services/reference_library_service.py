from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from app.schemas.analysis import (
    MetricBenchmark,
    ReferenceDimension,
    ReferenceIndicator,
    ReferenceLibraryResponse,
    ReferenceQuote,
)
from app.services.educator_taxonomy import (
    EDUCATOR_GROUPS,
    EDUCATOR_INDICATORS,
    INDICATOR_METRIC_BENCHMARKS,
)
from app.utils.text_stats import extract_wordcloud_keywords


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_REFERENCE_DATASET = ROOT_DIR / "data" / "samples" / "educator_interviews_import.csv"


class ReferenceLibraryService:
    def __init__(self, dataset_path: Path | None = None) -> None:
        self.dataset_path = dataset_path or DEFAULT_REFERENCE_DATASET

    def get_reference_library(self) -> ReferenceLibraryResponse:
        rows = self._load_rows()
        respondent_count = len(
            {
                str(row.get("respondent_id", "")).strip()
                for row in rows
                if str(row.get("respondent_id", "")).strip()
            }
        )

        dimensions: list[ReferenceDimension] = []
        for group in EDUCATOR_GROUPS:
            matched_rows = [
                row for row in rows if str(row.get("question_id", "")).strip() in group.question_ids
            ]
            texts = [str(row.get("text", "")).strip() for row in matched_rows if str(row.get("text", "")).strip()]
            group_indicators = [item for item in EDUCATOR_INDICATORS if item.group_id == group.id]

            dimensions.append(
                ReferenceDimension(
                    id=group.id,
                    name=group.name,
                    description=group.description,
                    question_ids=list(group.question_ids),
                    keyword_cues=self._merge_keywords(group_indicators),
                    excerpt_count=len(texts),
                    indicators=[
                        ReferenceIndicator(
                            id=indicator.id,
                            name=indicator.name,
                            aspect_type=indicator.aspect_type,
                            description=indicator.description,
                            question_ids=list(indicator.question_ids),
                            keyword_cues=list(indicator.cue_keywords),
                            metric_benchmarks=[
                                MetricBenchmark(
                                    id=benchmark.id,
                                    name=benchmark.name,
                                    unit=benchmark.unit,
                                    description=benchmark.description,
                                    low=benchmark.low,
                                    medium=benchmark.medium,
                                    high=benchmark.high,
                                )
                                for benchmark in INDICATOR_METRIC_BENCHMARKS
                            ],
                        )
                        for indicator in group_indicators
                    ],
                    highlight_terms=extract_wordcloud_keywords(texts, limit=10, min_count=2),
                    sample_quotes=self._pick_sample_quotes(matched_rows),
                )
            )

        return ReferenceLibraryResponse(
            source_name="教育家三重人格底库",
            source_file=self.dataset_path.name,
            total_excerpts=len(rows),
            total_respondents=respondent_count,
            dimensions=dimensions,
        )

    def _load_rows(self) -> list[dict[str, str]]:
        with self.dataset_path.open("r", encoding="utf-8-sig", newline="") as file:
            return [row for row in csv.DictReader(file) if str(row.get("text", "")).strip()]

    def _pick_sample_quotes(self, rows: list[dict[str, str]]) -> list[ReferenceQuote]:
        selected: list[ReferenceQuote] = []
        seen_respondents: set[str] = set()

        for row in sorted(rows, key=lambda item: len(str(item.get("text", ""))), reverse=True):
            respondent_id = str(row.get("respondent_id", "")).strip()
            text = str(row.get("text", "")).strip()
            if not text or respondent_id in seen_respondents:
                continue

            selected.append(
                ReferenceQuote(
                    respondent_name=str(row.get("respondent_name", "")).strip(),
                    question_id=str(row.get("question_id", "")).strip(),
                    question=str(row.get("question", "")).strip(),
                    text=text,
                )
            )
            seen_respondents.add(respondent_id)
            if len(selected) >= 3:
                break

        return selected

    def _merge_keywords(self, indicators) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for indicator in indicators:
            for keyword in indicator.cue_keywords:
                if keyword in seen:
                    continue
                seen.add(keyword)
                merged.append(keyword)
        return merged[:14]


@lru_cache(maxsize=1)
def get_reference_library_service() -> ReferenceLibraryService:
    return ReferenceLibraryService()
