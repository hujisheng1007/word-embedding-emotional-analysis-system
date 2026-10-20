from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import research_models  # noqa: F401
from app.db.base import Base
from app.schemas.knowledge import (
    EvaluationCase, KnowledgeSearchRequest, RetrievalEvaluationRequest,
)
from app.services.knowledge_service import KnowledgeService
from app.services.research_resource_service import ResearchResourceService


@pytest.fixture()
def services(tmp_path: Path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'knowledge.db').as_posix()}", future=True)

    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return ResearchResourceService(factory, tmp_path / "storage"), KnowledgeService(factory)


def test_search_keeps_source_locator_and_evaluation_is_reproducible(services) -> None:
    resources, knowledge = services
    target = resources.import_file(
        filename="dewey.txt",
        data="教育通过共同生活与沟通培养社会责任。\n\n学生在实践中形成合作意识。".encode(),
        title="民主与教育摘录", resource_type="book", educator_name="杜威",
        source_url="https://example.edu/dewey", copyright_status="authorized",
        fulltext_allowed=True, access_level="internal",
    )
    distractor = resources.import_file(
        filename="other.txt", data="课堂需要记录日常观察。".encode(),
        title="课堂观察", resource_type="note", copyright_status="authorized",
        fulltext_allowed=True, access_level="internal",
    )
    assert target.resource_id and distractor.resource_id

    response = knowledge.search(KnowledgeSearchRequest(
        query="教育 社会责任", resource_type="book", top_k=5
    ))
    assert response.hits[0].resource_id == target.resource_id
    assert response.hits[0].locator_type == "paragraph"
    assert response.hits[0].locator_value == "1"
    assert response.hits[0].source_url == "https://example.edu/dewey"

    evaluation = knowledge.evaluate(RetrievalEvaluationRequest(
        name="基线", top_k=5,
        cases=[EvaluationCase(query="教育 社会责任", expected_resource_ids=[target.resource_id])],
    ))
    assert evaluation.hit_rate_at_k == 1.0
    assert evaluation.mean_reciprocal_rank == 1.0
    assert evaluation.results[0].first_relevant_rank == 1
