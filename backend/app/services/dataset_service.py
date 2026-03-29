from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.schemas.analysis import (
    AnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    BatchAnalysisSummary,
    DatasetOption,
    KeywordCount,
    ScoreFactor,
)
from app.services.analysis_service import AnalysisService
from app.utils.text_stats import extract_wordcloud_keywords


ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_SAMPLES_DIR = ROOT_DIR / "data" / "samples"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DEFAULT_DATASET_PATH = DATA_PROCESSED_DIR / "educator_interviews_analysis.csv"
ANALYSIS_REQUIRED_COLUMNS = {
    "text",
    "category",
    "level",
    "score",
    "keywords",
    "rule_reason",
    "llm_explanation",
    "needs_attention",
}
TEXT_COLUMN_CANDIDATES = ["text", "文本", "内容", "body", "message", "comment"]


class DatasetService:
    def __init__(
        self,
        dataset_path: Path | None = None,
        analysis_service: AnalysisService | None = None,
    ) -> None:
        self.dataset_path = dataset_path or DEFAULT_DATASET_PATH
        self.analysis_service = analysis_service or AnalysisService()
        self._analysis_cache: dict[str, tuple[float, BatchAnalysisResponse]] = {}

    def get_default_dataset_id(self) -> str:
        return self._build_dataset_id(self.dataset_path)

    def list_datasets(self) -> list[DatasetOption]:
        datasets: list[DatasetOption] = []
        for path in self._iter_dataset_files():
            descriptor = self._build_dataset_option(path)
            if descriptor is not None:
                datasets.append(descriptor)

        datasets.sort(
            key=lambda item: (
                not item.is_default,
                0 if item.data_kind == "analysis" else 1,
                item.name,
            )
        )
        return datasets

    def get_default_dataset_analysis(self) -> BatchAnalysisResponse:
        return self.get_dataset_analysis(self.get_default_dataset_id())

    def get_dataset_analysis(self, dataset_id: str) -> BatchAnalysisResponse:
        path = self._resolve_dataset_path(dataset_id)
        headers = self._read_headers(path)
        normalized_headers = {header.strip() for header in headers}

        if self._is_analysis_csv(normalized_headers):
            results = self._load_results_from_analysis_csv(path)
            return BatchAnalysisResponse(summary=self._build_summary(results), results=results)

        text_column = self._find_text_column(headers)
        if not text_column:
            raise FileNotFoundError(f"Dataset does not contain a readable text column: {path}")

        cache_key = str(path.resolve())
        mtime = path.stat().st_mtime
        cached = self._analysis_cache.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]

        texts = self._load_texts_from_import_csv(path, text_column)
        response = self.analysis_service.analyze_batch(BatchAnalysisRequest(texts=texts))
        self._analysis_cache[cache_key] = (mtime, response)
        return response

    def _iter_dataset_files(self) -> list[Path]:
        ordered_paths: list[Path] = []
        seen: set[Path] = set()
        for directory in (DATA_PROCESSED_DIR, DATA_SAMPLES_DIR):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.csv")):
                if "rule_hit_review" in path.stem:
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                ordered_paths.append(path)
        return ordered_paths

    def _build_dataset_option(self, path: Path) -> DatasetOption | None:
        headers = self._read_headers(path)
        if not headers:
            return None

        normalized_headers = {header.strip() for header in headers}
        data_kind: str | None = None
        record_count = 0
        attention_count = 0

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if self._is_analysis_csv(normalized_headers):
                data_kind = "analysis"
                for row in reader:
                    if not any((value or "").strip() for value in row.values()):
                        continue
                    record_count += 1
                    if str(row.get("needs_attention", "")).strip().lower() == "true":
                        attention_count += 1
            else:
                text_column = self._find_text_column(headers)
                if not text_column:
                    return None
                data_kind = "import"
                for row in reader:
                    if str(row.get(text_column, "")).strip():
                        record_count += 1

        name, description = self._describe_dataset(path, data_kind)
        updated_at = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        return DatasetOption(
            id=self._build_dataset_id(path),
            name=name,
            description=description,
            file_name=path.name,
            data_kind=data_kind,
            record_count=record_count,
            attention_count=attention_count,
            updated_at=updated_at,
            is_default=path.resolve() == self.dataset_path.resolve(),
        )

    def _read_headers(self, path: Path) -> list[str]:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)
            return next(reader, [])

    def _resolve_dataset_path(self, dataset_id: str) -> Path:
        for path in self._iter_dataset_files():
            if self._build_dataset_id(path) == dataset_id:
                return path
        raise FileNotFoundError(f"Dataset not found: {dataset_id}")

    def _build_dataset_id(self, path: Path) -> str:
        return path.stem.replace("_", "-").lower()

    def _is_analysis_csv(self, headers: set[str]) -> bool:
        return ANALYSIS_REQUIRED_COLUMNS.issubset(headers)

    def _find_text_column(self, headers: list[str]) -> str | None:
        header_map = {header.strip().lower(): header for header in headers}
        for candidate in TEXT_COLUMN_CANDIDATES:
            match = header_map.get(candidate.lower())
            if match:
                return match
        return None

    def _load_results_from_analysis_csv(self, path: Path) -> list[AnalysisResult]:
        results: list[AnalysisResult] = []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if not str(row.get("text", "")).strip():
                    continue
                keywords = [item for item in str(row.get("keywords", "")).split("|") if item]
                score_breakdown = self._parse_score_breakdown(row.get("score_breakdown", ""))
                results.append(
                    AnalysisResult(
                        text=str(row["text"]),
                        category=str(row["category"]),
                        level=str(row["level"]),
                        score=float(row["score"]),
                        keywords=keywords,
                        rule_reason=str(row["rule_reason"]),
                        llm_explanation=str(row["llm_explanation"]),
                        needs_attention=str(row["needs_attention"]).strip().lower() == "true",
                        score_breakdown=score_breakdown,
                    )
                )
        return results

    def _parse_score_breakdown(self, raw_value: str) -> list[ScoreFactor]:
        if not raw_value.strip():
            return []
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        factors: list[ScoreFactor] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                factors.append(ScoreFactor(**item))
            except Exception:
                continue
        return factors

    def _load_texts_from_import_csv(self, path: Path, text_column: str) -> list[str]:
        texts: list[str] = []
        seen: set[str] = set()
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                text = self._normalize_text(str(row.get(text_column, "")))
                if not text or text in seen:
                    continue
                seen.add(text)
                texts.append(text)
        return texts

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.replace("\u3000", " ").split()).strip()

    def _describe_dataset(self, path: Path, data_kind: str) -> tuple[str, str]:
        mapping = {
            "educator_interviews_analysis.csv": (
                "教师访谈分析结果",
                "基于教师访谈切片生成的分析结果集，适合直接展示统计、词云和风险详情。",
            ),
            "educator_interviews_import.csv": (
                "教师访谈原始切片",
                "已完成结构化切片的教师访谈文本，可重新走当前分析链路用于校验规则和模型。",
            ),
            "demo_texts.csv": (
                "演示样本集",
                "体量较小的手工样本，适合快速演示单条与批量分析效果。",
            ),
        }
        if path.name in mapping:
            return mapping[path.name]

        stem_name = path.stem.replace("_", " ").strip()
        if data_kind == "analysis":
            return stem_name, "已包含分析结果的 CSV 数据集。"
        return stem_name, "可导入并重新分析的原始文本数据集。"

    def _build_summary(self, results: list[AnalysisResult]) -> BatchAnalysisSummary:
        category_counter = Counter(result.category for result in results)
        level_counter = Counter(result.level for result in results)
        keyword_counter = Counter(keyword for result in results for keyword in result.keywords)

        top_keywords = [
            KeywordCount(keyword=keyword, count=count)
            for keyword, count in keyword_counter.most_common(10)
        ]

        return BatchAnalysisSummary(
            total=len(results),
            category_distribution=dict(category_counter),
            level_distribution=dict(level_counter),
            top_keywords=top_keywords,
            wordcloud_keywords=extract_wordcloud_keywords([result.text for result in results]),
            attention_count=sum(1 for result in results if result.needs_attention),
            high_risk_texts=[result for result in results if result.needs_attention][:10],
        )
