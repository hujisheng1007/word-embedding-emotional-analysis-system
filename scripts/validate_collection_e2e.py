from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from app.api.routes import collection as collection_routes
from app.api.routes import research_resources as resource_routes
from app.api.routes import knowledge as knowledge_routes
from app.collectors.crossref import CrossrefWorksAdapter
from app.collectors.wikimedia import WikimediaVideoAdapter
from app.db import research_models  # noqa: F401
from app.db.base import Base
from app.db.research_models import (
    EducatorPerson, PersonalityEvidence, ResearchResource, Transcript, VideoAsset,
)
from app.main import app
from app.schemas.collection import CollectionJobCreate
from app.schemas.knowledge import EvaluationCase, KnowledgeSearchRequest, RetrievalEvaluationRequest
from app.services.collection_service import CollectionService
from app.services.knowledge_service import KnowledgeService
from app.services.research_resource_service import ResearchResourceService


BOOK_URL = "https://www.gutenberg.org/cache/epub/852/pg852.txt"
BOOK_PAGE = "https://www.gutenberg.org/ebooks/852"
VIDEO_TITLE = "File:EN simpleshow foundation Montessori explainer video.webm"


def build_services(database: Path, storage: Path):
    engine = create_engine(f"sqlite:///{database.as_posix()}", future=True)

    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return (
        engine, factory, CollectionService(factory), ResearchResourceService(factory, storage),
        KnowledgeService(factory),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run legal live-source E2E validation in an isolated database")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)
    args.storage.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    engine, factory, collection, resources, knowledge = build_services(args.database, args.storage)
    collection.ensure_sources()
    report: dict = {"database": str(args.database), "checks": {}}

    # A. Real educator identity and source-backed candidate fact from Wikidata CC0.
    wikidata = next(source for source in collection.list_sources() if source.adapter_key == "wikidata")
    person_job = collection.create_job(CollectionJobCreate(
        source_id=wikidata.id, query="Cai Yuanpei", educator_name="蔡元培",
        language="en", limit=1,
    ))
    collection.run_job(person_job)
    person = collection.list_people("Cai Yuanpei")[0]
    report["checks"]["A_person"] = {
        "status": collection.list_jobs()[0].status,
        "job_id": person_job,
        "person_id": person.id,
        "name": person.display_name,
        "source": person.identities[0]["canonical_url"],
        "review_status": person.identities[0]["review_status"],
        "frontend_api": "/api/collection/people?keyword=Cai%20Yuanpei",
    }

    # B/C. Real Commons video metadata plus official German TimedText track.
    commons = WikimediaVideoAdapter()
    video_candidates = commons.search(
        "EN simpleshow foundation Montessori explainer video", 10,
        educator_name="Maria Montessori",
    )
    video_candidate = next(item for item in video_candidates if item.external_id == VIDEO_TITLE)
    collection._ingest_candidate(video_candidate, commons)
    video = next(item for item in collection.list_videos() if item.title.startswith("EN simpleshow"))
    transcript_id = collection.import_subtitle(
        video.id, language="de", origin="official_subtitle", content="",
        fetch_from_source=True,
    )
    video = next(item for item in collection.list_videos() if item.id == video.id)
    report["checks"]["B_video"] = {
        "status": "succeeded", "resource_id": video.resource_id,
        "video_id": video.id, "title": video.title, "source": video.page_url,
        "license": video.license_code, "embed_allowed": video.embed_allowed,
        "frontend_api": "/api/collection/videos",
    }
    report["checks"]["C_transcript"] = {
        "status": "succeeded", "transcript_id": transcript_id,
        "origin": video.transcripts[0].origin, "language": video.transcripts[0].language,
        "cue_count": len(video.transcripts[0].cues),
        "first_timestamp_ms": video.transcripts[0].cues[0].start_ms,
        "review_status": video.transcripts[0].review_status,
    }

    # D. Crossref is the no-key scholarly metadata fallback; DOI is persisted for deduplication.
    crossref = CrossrefWorksAdapter()
    paper_candidate = crossref.search("Maria Montessori education", 1)[0]
    collection._ingest_candidate(paper_candidate, crossref)
    with factory() as session:
        paper = session.scalar(select(ResearchResource).where(
            ResearchResource.source_url == paper_candidate.source_url
        ))
        assert paper is not None
    report["checks"]["D_paper"] = {
        "status": "succeeded", "resource_id": paper.id,
        "title": paper.title, "doi": paper_candidate.identifiers.get("doi", ""),
        "source": paper.source_url, "fulltext_saved": False,
        "frontend_api": f"/api/research-resources/{paper.id}",
    }

    # E. Public-domain local file path: download once, then use the normal authorized file importer.
    response = httpx.get(BOOK_URL, timeout=60, follow_redirects=True)
    response.raise_for_status()
    book_result = resources.import_file(
        filename="democracy-and-education.txt", data=response.content,
        media_type="text/plain", title="Democracy and Education",
        resource_type="book", authors=["John Dewey"], educator_name="John Dewey",
        source_institution="Project Gutenberg", source_url=BOOK_PAGE,
        copyright_status="public_domain", fulltext_allowed=True,
        access_level="public", citation_text="John Dewey. Democracy and Education. Project Gutenberg eBook #852.",
    )
    assert book_result.resource_id
    book_analysis = collection.analyze_resource(book_result.resource_id)
    book_detail = resources.get_resource(book_result.resource_id)
    assert book_detail is not None
    report["checks"]["E_book"] = {
        "status": "succeeded", "resource_id": book_result.resource_id,
        "source": BOOK_PAGE, "license": "public_domain",
        "segment_count": len(book_detail.segments), "analysis_run_id": book_analysis.run_id,
        "evidence_count": len(book_analysis.evidence),
        "frontend_api": f"/api/research-resources/{book_result.resource_id}",
    }

    retrieval = knowledge.search(KnowledgeSearchRequest(
        query="education social responsibility communication", resource_type="book", top_k=10,
    ))
    evaluation = knowledge.evaluate(RetrievalEvaluationRequest(
        name="public-domain-book-live-e2e", top_k=10,
        cases=[EvaluationCase(
            query="education social responsibility communication",
            expected_resource_ids=[book_result.resource_id], resource_type="book",
        )],
    ))
    report["checks"]["F_knowledge_retrieval"] = {
        "status": "succeeded" if retrieval.hits and evaluation.hit_rate_at_k == 1 else "failed",
        "query_run_id": retrieval.run_id, "top_hit_resource_id": retrieval.hits[0].resource_id,
        "top_hit_locator": f"{retrieval.hits[0].locator_type}:{retrieval.hits[0].locator_value}",
        "evaluation_run_id": evaluation.run_id, "hit_rate_at_10": evaluation.hit_rate_at_k,
        "mrr": evaluation.mean_reciprocal_rank, "frontend_api": "/api/knowledge/search",
    }

    # Verify the exact JSON endpoints consumed by the Vue pages against the isolated DB.
    collection_routes.service = collection
    resource_routes.service = resources
    knowledge_routes.service = knowledge
    with TestClient(app) as client:
        api_checks = {
            "people": client.get("/api/collection/people").status_code,
            "videos": client.get("/api/collection/videos").status_code,
            "resources": client.get("/api/research-resources").status_code,
            "book_detail": client.get(f"/api/research-resources/{book_result.resource_id}").status_code,
            "knowledge_search": client.post("/api/knowledge/search", json={
                "query": "education communication", "resource_type": "book", "top_k": 5,
            }).status_code,
        }
    report["frontend_api_checks"] = api_checks

    with factory() as session:
        report["database_counts"] = {
            "educator_persons": int(session.scalar(select(func.count()).select_from(EducatorPerson)) or 0),
            "research_resources": int(session.scalar(select(func.count()).select_from(ResearchResource)) or 0),
            "video_assets": int(session.scalar(select(func.count()).select_from(VideoAsset)) or 0),
            "transcripts": int(session.scalar(select(func.count()).select_from(Transcript)) or 0),
            "personality_evidence": int(session.scalar(select(func.count()).select_from(PersonalityEvidence)) or 0),
        }
    report["all_passed"] = all(
        check.get("status") == "succeeded" for check in report["checks"].values()
    ) and all(status == 200 for status in report["frontend_api_checks"].values())
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
