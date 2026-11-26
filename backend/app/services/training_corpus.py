from sqlalchemy import case, inspect, select

from app.db.models import CorpusDataset, CorpusRecord
from app.services.knowledge_service import KnowledgeService, _tokens
from app.services.practice_service import normalize_term


INTERVIEW_DATASETS = ("educator-interviews-import", "educator-interviews-analysis")


class TrainingCorpus:
    def __init__(self, factory) -> None:
        self.factory = factory
        self.scanned = 0
        self._records: list[tuple] | None = None

    def _load(self) -> list[tuple]:
        if self._records is not None:
            return self._records
        with self.factory() as session:
            if not inspect(session.get_bind()).has_table(CorpusRecord.__tablename__):
                self._records = []
                return self._records
            rows = session.execute(
                select(CorpusRecord.id, CorpusRecord.text, CorpusDataset.name, CorpusDataset.file_name)
                .join(CorpusDataset, CorpusDataset.id == CorpusRecord.dataset_id)
                .where(CorpusDataset.id.in_(INTERVIEW_DATASETS), CorpusDataset.domain == "education")
                .order_by(case((CorpusDataset.data_kind == "import", 0), else_=1), CorpusRecord.id)
            )
            records = []
            seen = set()
            for record_id, text, title, file_name in rows:
                self.scanned += 1
                normalized = normalize_term(text)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                records.append((record_id, text, title, file_name, normalized))
        self._records = records
        return records

    def has_records(self) -> bool:
        return bool(self._load())

    def search(self, queries: list[str], limit: int) -> dict[str, dict]:
        terms_by_query = {
            query: {term for term in _tokens(query) if len(term) > 1}
            for query in dict.fromkeys(normalize_term(value) for value in queries)
        }
        ranked = []
        for record_id, text, title, file_name, normalized in self._load():
            best_score = 0.0
            best_query = ""
            for query, terms in terms_by_query.items():
                if not terms or (query not in normalized and sum(term in normalized for term in terms) < 2):
                    continue
                score = KnowledgeService._score(query, terms, "", normalized) / len(terms)
                if score > best_score:
                    best_score, best_query = score, query
            if best_score > 0:
                ranked.append((best_score, record_id, text, title, file_name, best_query))
        evidence = {}
        for _, record_id, text, title, file_name, query in sorted(ranked, key=lambda row: (-row[0], row[1]))[:limit]:
            excerpt = self._excerpt(text, query)
            key = f"corpus:{record_id}"
            evidence[key] = {
                "id": key, "kind": "interview", "quote": excerpt, "field": "interview",
                "source_title": title, "locator_type": "corpus_record", "locator_value": str(record_id),
                "source_file": file_name,
            }
        return evidence

    @staticmethod
    def _excerpt(text: str, query: str) -> str:
        if len(text) <= 700:
            return text
        lowered = text.casefold()
        match = lowered.find(query)
        if match < 0:
            match = min((position for term in _tokens(query) if (position := lowered.find(term)) >= 0), default=0)
        start = max(0, min(match - 170, len(text) - 700))
        return text[start:start + 700]
