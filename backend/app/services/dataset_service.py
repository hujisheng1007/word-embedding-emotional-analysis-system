from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from app.core.settings import get_settings
from app.db import CorpusDataset, CorpusRecord, get_session_factory, init_database
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
DEFAULT_DATASET_PATH = DATA_SAMPLES_DIR / "demo_texts.csv"
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

        settings = get_settings()
        self.database_enabled = settings.database_enabled
        self._session_factory = None
        if self.database_enabled:
            try:
                init_database()
                self._session_factory = get_session_factory()
                self._bootstrap_database_from_csv_if_empty()
            except Exception:
                self.database_enabled = False
                self._session_factory = None

    def get_default_dataset_id(self) -> str:
        if self.database_enabled and self._session_factory is not None:
            default_id = self._get_default_dataset_id_from_db()
            if default_id:
                return default_id
        return self._build_dataset_id(self.dataset_path)

    def list_datasets(self) -> list[DatasetOption]:
        if self.database_enabled and self._session_factory is not None:
            datasets = self._list_datasets_from_db()
            if datasets:
                return datasets
        return self._list_datasets_from_csv()

    def get_default_dataset_analysis(self) -> BatchAnalysisResponse:
        return self.get_dataset_analysis(self.get_default_dataset_id())

    def get_dataset_analysis(self, dataset_id: str) -> BatchAnalysisResponse:
        if self.database_enabled and self._session_factory is not None:
            try:
                return self._get_dataset_analysis_from_db(dataset_id)
            except FileNotFoundError:
                raise
            except Exception:
                pass
        return self._get_dataset_analysis_from_csv(dataset_id)

    def _get_default_dataset_id_from_db(self) -> str | None:
        assert self._session_factory is not None
        with self._session_factory() as session:
            dataset = session.execute(
                select(CorpusDataset).order_by(CorpusDataset.is_default.desc(), CorpusDataset.name.asc())
            ).scalars().first()
            if dataset is None:
                return None
            return dataset.id

    def _list_datasets_from_db(self) -> list[DatasetOption]:
        assert self._session_factory is not None
        with self._session_factory() as session:
            datasets = session.execute(
                select(CorpusDataset).order_by(CorpusDataset.is_default.desc(), CorpusDataset.name.asc())
            ).scalars().all()

            options: list[DatasetOption] = []
            for dataset in datasets:
                record_count = (
                    session.scalar(
                        select(func.count(CorpusRecord.id)).where(CorpusRecord.dataset_id == dataset.id)
                    )
                    or 0
                )
                attention_count = (
                    session.scalar(
                        select(func.count(CorpusRecord.id)).where(
                            CorpusRecord.dataset_id == dataset.id,
                            CorpusRecord.needs_attention.is_(True),
                        )
                    )
                    or 0
                )
                options.append(
                    DatasetOption(
                        id=dataset.id,
                        name=dataset.name,
                        description=dataset.description,
                        file_name=dataset.file_name,
                        data_kind=dataset.data_kind,
                        domain=dataset.domain,
                        source=dataset.source,
                        record_count=record_count,
                        attention_count=attention_count,
                        updated_at=dataset.updated_at.strftime("%Y-%m-%d %H:%M"),
                        is_default=dataset.is_default,
                    )
                )
            return options

    def _get_dataset_analysis_from_db(self, dataset_id: str) -> BatchAnalysisResponse:
        assert self._session_factory is not None
        with self._session_factory() as session:
            dataset = session.get(CorpusDataset, dataset_id)
            if dataset is None:
                raise FileNotFoundError(f"Dataset not found: {dataset_id}")

            records = session.execute(
                select(CorpusRecord).where(CorpusRecord.dataset_id == dataset_id).order_by(CorpusRecord.id.asc())
            ).scalars().all()

            if not records:
                return BatchAnalysisResponse(summary=self._build_summary([]), results=[])

            if dataset.data_kind == "analysis":
                results = [self._build_analysis_result_from_record(record) for record in records if record.text.strip()]
                return BatchAnalysisResponse(summary=self._build_summary(results), results=results)

            cache_key = (
                f"db:{dataset.id}:"
                f"{dataset.updated_at.timestamp()}:"
                f"{len(records)}"
            )
            cached = self._analysis_cache.get(cache_key)
            if cached:
                return cached[1]

            seen: set[str] = set()
            texts: list[str] = []
            for record in records:
                text = self._normalize_text(record.text)
                if not text or text in seen:
                    continue
                seen.add(text)
                texts.append(text)

            response = self.analysis_service.analyze_batch(BatchAnalysisRequest(texts=texts))
            self._analysis_cache[cache_key] = (dataset.updated_at.timestamp(), response)
            return response

    def _build_analysis_result_from_record(self, record: CorpusRecord) -> AnalysisResult:
        keywords = self._parse_json_list(record.keywords_json)
        score_breakdown = self._parse_score_breakdown(record.score_breakdown_json)
        return AnalysisResult(
            text=record.text,
            category=record.category,
            level=record.level,
            score=float(record.score),
            keywords=keywords,
            rule_reason=record.rule_reason,
            llm_explanation=record.llm_explanation,
            needs_attention=record.needs_attention,
            score_breakdown=score_breakdown,
        )

    def _bootstrap_database_from_csv_if_empty(self) -> None:
        assert self._session_factory is not None
        with self._session_factory() as session:
            dataset_count = session.scalar(select(func.count(CorpusDataset.id))) or 0
            if dataset_count > 0:
                return

            paths = self._iter_dataset_files()
            if not paths:
                return

            default_id = self._pick_default_dataset_id(paths)
            for path in paths:
                headers = self._read_headers(path)
                if not headers:
                    continue
                normalized_headers = {header.strip() for header in headers}
                if self._is_analysis_csv(normalized_headers):
                    data_kind = "analysis"
                    records = self._build_db_records_from_analysis_csv(path)
                else:
                    text_column = self._find_text_column(headers)
                    if not text_column:
                        continue
                    data_kind = "import"
                    records = self._build_db_records_from_import_csv(path, text_column)

                name, description = self._describe_dataset(path, data_kind)
                domain = self._infer_domain(path)
                dataset = CorpusDataset(
                    id=self._build_dataset_id(path),
                    name=name,
                    description=description,
                    file_name=path.name,
                    data_kind=data_kind,
                    domain=domain,
                    source="database",
                    is_default=self._build_dataset_id(path) == default_id,
                    updated_at=datetime.fromtimestamp(path.stat().st_mtime),
                )
                dataset.records = records
                session.add(dataset)

            session.commit()

    def _pick_default_dataset_id(self, paths: list[Path]) -> str:
        for path in paths:
            if "educator" not in path.stem.lower():
                return self._build_dataset_id(path)
        return self._build_dataset_id(paths[0])

    def _infer_domain(self, path: Path) -> str:
        name = path.name.lower()
        if "educator" in name:
            return "education"
        return "general"

    def _build_db_records_from_analysis_csv(self, path: Path) -> list[CorpusRecord]:
        records: list[CorpusRecord] = []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                text = self._normalize_text(str(row.get("text", "")))
                if not text:
                    continue
                keywords = [item for item in str(row.get("keywords", "")).split("|") if item]
                raw_breakdown = str(row.get("score_breakdown", "[]")).strip() or "[]"
                try:
                    # Ensure valid JSON for downstream parsing.
                    json.loads(raw_breakdown)
                except json.JSONDecodeError:
                    raw_breakdown = "[]"

                records.append(
                    CorpusRecord(
                        text=text,
                        category=str(row.get("category", "")),
                        level=str(row.get("level", "")),
                        score=self._safe_float(row.get("score", 0.0)),
                        keywords_json=json.dumps(keywords, ensure_ascii=False),
                        score_breakdown_json=raw_breakdown,
                        rule_reason=str(row.get("rule_reason", "")),
                        llm_explanation=str(row.get("llm_explanation", "")),
                        needs_attention=str(row.get("needs_attention", "")).strip().lower() == "true",
                    )
                )
        return records

    def _build_db_records_from_import_csv(self, path: Path, text_column: str) -> list[CorpusRecord]:
        records: list[CorpusRecord] = []
        seen: set[str] = set()
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                text = self._normalize_text(str(row.get(text_column, "")))
                if not text or text in seen:
                    continue
                seen.add(text)
                records.append(CorpusRecord(text=text))
        return records

    def _parse_json_list(self, raw: str) -> list[str]:
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        return [str(item) for item in payload if str(item).strip()]

    def _safe_float(self, value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _list_datasets_from_csv(self) -> list[DatasetOption]:
        datasets: list[DatasetOption] = []
        for path in self._iter_dataset_files():
            descriptor = self._build_dataset_option(path)
            if descriptor is not None:
                datasets.append(descriptor)

        datasets.sort(
            key=lambda item: (
                not item.is_default,
                item.name,
            )
        )
        return datasets

    def _get_dataset_analysis_from_csv(self, dataset_id: str) -> BatchAnalysisResponse:
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
            domain=self._infer_domain(path),
            source="csv",
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
                "教育家访谈分析结果",
                "教育家访谈语料的已分析结果集，可直接用于展示分布与重点文本。",
            ),
            "educator_interviews_import.csv": (
                "教育家访谈语料（子集）",
                "教育家访谈导入语料，仅作为多语料体系中的一个领域子集。",
            ),
            "demo_texts.csv": (
                "通用演示语料",
                "小规模通用文本语料，可作为默认入口快速演示全流程。",
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
