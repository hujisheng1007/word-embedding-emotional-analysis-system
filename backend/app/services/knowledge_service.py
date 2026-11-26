from __future__ import annotations

import json
import math
import re
from datetime import datetime
from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.orm import load_only, sessionmaker

from app.db.research_models import (
    EducatorPerson, KnowledgeQueryRun, ResearchResource, ResourceSegment,
    RetrievalEvaluationRun,
)
from app.db.session import get_session_factory
from app.schemas.knowledge import (
    EvaluationCaseResult, KnowledgeHit, KnowledgeSearchRequest, KnowledgeSearchResponse,
    RetrievalEvaluationRequest, RetrievalEvaluationResponse,
)


_LATIN_OR_NUMBER = re.compile(r"[a-z0-9]+")
_CHINESE_RUN = re.compile(r"[\u3400-\u9fff]+")


class KnowledgeSchemaNotReady(RuntimeError):
    pass


def _tokens(text: str) -> set[str]:
    normalized = text.lower()
    result = set(_LATIN_OR_NUMBER.findall(normalized))
    for run in _CHINESE_RUN.findall(normalized):
        if len(run) == 1:
            result.add(run)
        else:
            result.update(run[index:index + 2] for index in range(len(run) - 1))
    return {token for token in result if token.strip()}


class KnowledgeService:
    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        self.session_factory = session_factory or get_session_factory()

    def _check_schema(self) -> None:
        with self.session_factory() as session:
            tables = set(inspect(session.get_bind()).get_table_names())
        required = {"knowledge_query_runs", "retrieval_evaluation_runs", "resource_segments"}
        if missing := required - tables:
            raise KnowledgeSchemaNotReady(
                "知识检索模块尚未初始化，请执行 `alembic upgrade head`。缺少表：" + "、".join(sorted(missing))
            )

    @staticmethod
    def _score(query: str, terms: set[str], title: str, text: str) -> float:
        lowered = text.lower()
        score = sum(1.0 + math.log1p(lowered.count(term)) for term in terms if term in lowered)
        if query.lower() in lowered:
            score += 4.0
        title_lower = title.lower()
        score += sum(2.0 for term in terms if term in title_lower)
        if query.lower() in title_lower:
            score += 5.0
        return round(score, 6)

    @staticmethod
    def _hit(segment: ResourceSegment, resource: ResearchResource, person: EducatorPerson | None,
             score: float, excerpt: str) -> KnowledgeHit:
        return KnowledgeHit(
            resource_id=resource.id, resource_title=resource.title,
            resource_type=resource.resource_type, educator_name=person.display_name if person else "",
            source_url=resource.source_url, copyright_status=resource.copyright_status,
            segment_id=segment.id, locator_type=segment.locator_type,
            locator_value=segment.locator_value, excerpt=excerpt, score=score,
        )

    @staticmethod
    def _resource_segments():
        return (
            select(ResourceSegment, ResearchResource, EducatorPerson)
            .join(ResearchResource, ResourceSegment.resource_id == ResearchResource.id)
            .outerjoin(EducatorPerson, ResearchResource.educator_person_id == EducatorPerson.id)
            .options(
                load_only(ResearchResource.id, ResearchResource.title, ResearchResource.resource_type,
                          ResearchResource.source_url, ResearchResource.copyright_status),
                load_only(EducatorPerson.display_name),
            )
        )

    def training_materials(self, queries: list[str], limit: int = 4) -> list[KnowledgeHit]:
        terms_by_query = {
            query: {term for term in _tokens(query) if len(term) > 1}
            for query in dict.fromkeys(value.strip().lower() for value in queries if value.strip())
        }
        if not any(terms_by_query.values()):
            return []
        matches: dict[str, KnowledgeHit] = {}
        statement = self._resource_segments().where(
            ResearchResource.fulltext_allowed.is_(True),
            ResearchResource.copyright_status != "restricted",
            ResearchResource.access_level.in_(("internal", "public")),
        ).order_by(ResourceSegment.resource_id, ResourceSegment.ordinal)
        with self.session_factory() as session:
            for segment, resource, person in session.execute(statement.execution_options(yield_per=200)):
                text = segment.text.lower()
                title = resource.title.lower()
                best_score = 0.0
                best_query = ""
                for query, terms in terms_by_query.items():
                    if not terms or (query not in title and query not in text and sum(term in text for term in terms) < 2):
                        continue
                    score = self._score(query, terms, title, text) / len(terms)
                    if score > best_score:
                        best_score, best_query = score, query
                previous = matches.get(resource.id)
                if best_score <= 0 or (previous and best_score <= previous.score):
                    continue
                position = text.find(best_query)
                if position < 0:
                    position = min((start for term in terms_by_query[best_query] if (start := text.find(term)) >= 0), default=0)
                start = max(0, min(position - 100, len(text) - 360))
                matches[resource.id] = self._hit(segment, resource, person, best_score, segment.text[start:start + 360])
        return sorted(matches.values(), key=lambda hit: (-hit.score, hit.resource_title))[:limit]

    def search(self, payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        self._check_schema()
        query = payload.query.strip()
        terms = _tokens(query)
        with self.session_factory() as session:
            statement = self._resource_segments()
            if payload.educator_name.strip():
                statement = statement.where(EducatorPerson.display_name.contains(payload.educator_name.strip()))
            if payload.resource_type.strip():
                statement = statement.where(ResearchResource.resource_type == payload.resource_type.strip())
            scored: list[KnowledgeHit] = []
            # Stream the full corpus so later-imported books remain searchable.
            # A fixed prefix silently excluded resources once the library grew.
            for segment, resource, person in session.execute(statement.execution_options(yield_per=500)):
                score = self._score(query, terms, resource.title, segment.text)
                if score <= 0:
                    continue
                excerpt = segment.text.strip()
                if len(excerpt) > 360:
                    excerpt = excerpt[:357] + "..."
                scored.append(self._hit(segment, resource, person, score, excerpt))
            scored.sort(key=lambda item: (-item.score, item.resource_id, item.locator_value))
            hits = scored[:payload.top_k]
            run = KnowledgeQueryRun(
                id=str(uuid4()), query=query,
                filters_json=json.dumps({
                    "educator_name": payload.educator_name,
                    "resource_type": payload.resource_type,
                }, ensure_ascii=False),
                top_k=payload.top_k,
                results_json=json.dumps([item.model_dump() for item in hits], ensure_ascii=False),
            )
            session.add(run)
            session.commit()
            return KnowledgeSearchResponse(
                run_id=run.id, query=query, total_candidates=len(scored), hits=hits,
            )

    def evaluate(self, payload: RetrievalEvaluationRequest) -> RetrievalEvaluationResponse:
        results: list[EvaluationCaseResult] = []
        reciprocal_ranks: list[float] = []
        for case in payload.cases:
            search = self.search(KnowledgeSearchRequest(
                query=case.query, educator_name=case.educator_name,
                resource_type=case.resource_type, top_k=payload.top_k,
            ))
            unique_resources: list[str] = []
            for hit in search.hits:
                if hit.resource_id not in unique_resources:
                    unique_resources.append(hit.resource_id)
            first_rank = next(
                (index for index, resource_id in enumerate(unique_resources, 1)
                 if resource_id in case.expected_resource_ids),
                None,
            )
            results.append(EvaluationCaseResult(
                query=case.query, expected_resource_ids=case.expected_resource_ids,
                retrieved_resource_ids=unique_resources,
                first_relevant_rank=first_rank, hit=first_rank is not None,
            ))
            reciprocal_ranks.append(1 / first_rank if first_rank else 0.0)
        hit_rate = sum(item.hit for item in results) / len(results)
        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
        created_at = datetime.utcnow()
        with self.session_factory() as session:
            run = RetrievalEvaluationRun(
                id=str(uuid4()), name=payload.name,
                dataset_json=json.dumps([item.model_dump() for item in payload.cases], ensure_ascii=False),
                metrics_json=json.dumps({
                    "top_k": payload.top_k, "hit_rate_at_k": hit_rate,
                    "mean_reciprocal_rank": mrr,
                    "results": [item.model_dump() for item in results],
                }, ensure_ascii=False),
                created_at=created_at,
            )
            session.add(run)
            session.commit()
            return RetrievalEvaluationResponse(
                run_id=run.id, name=run.name, top_k=payload.top_k,
                case_count=len(results), hit_rate_at_k=round(hit_rate, 6),
                mean_reciprocal_rank=round(mrr, 6), results=results,
                created_at=created_at,
            )
