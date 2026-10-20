from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.collectors.base import Candidate
from app.db import research_models  # noqa: F401
from app.db.base import Base
from app.db.research_models import CollectionJob, ResourceIdentifier, VideoAsset
from app.schemas.collection import CollectionJobCreate
from app.services import collection_service as module
from app.services.collection_service import CollectionService


@pytest.fixture()
def collection_service(tmp_path: Path) -> CollectionService:
    engine = create_engine(f"sqlite:///{(tmp_path / 'collection.db').as_posix()}", future=True)

    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return CollectionService(factory)


class FakeAdapter:
    key = "wikidata"

    def search(self, query: str, limit: int = 10, **_options):
        return [Candidate(
            kind="person", external_id="Q-test-tao", title="陶行知", educator_name="陶行知",
            source_name="Wikidata", source_url="https://www.wikidata.org/wiki/Q-test-tao",
            description="中国教育家（待人工核验候选描述）", identifiers={"wikidata": "Q-test-tao"},
            copyright_status="public_domain", license_code="CC0-1.0",
        )]


class FakeVideoAdapter:
    key = "wikimedia_commons"


def test_person_collection_job_writes_traceable_candidate_and_logs(
    collection_service: CollectionService, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = collection_service.list_sources()
    wikidata = next(source for source in sources if source.adapter_key == "wikidata")
    job_id = collection_service.create_job(CollectionJobCreate(
        source_id=wikidata.id, query="陶行知", educator_name="陶行知", limit=1
    ))
    monkeypatch.setattr(module, "get_adapter", lambda _key: FakeAdapter())

    collection_service.run_job(job_id)

    jobs = collection_service.list_jobs()
    assert jobs[0].id == job_id
    assert jobs[0].status == "succeeded"
    assert jobs[0].success_count == 1
    people = collection_service.list_people("陶行知")
    assert people[0].display_name == "陶行知"
    assert people[0].facts[0].source_url.endswith("Q-test-tao")
    assert people[0].facts[0].review_status == "pending"
    assert {log.event for log in collection_service.list_logs(job_id)} >= {"started", "completed"}


def test_video_subtitle_timestamps_and_personality_evidence(collection_service: CollectionService) -> None:
    candidate = Candidate(
        kind="video", external_id="File:education.webm", title="教育实践公开视频",
        source_name="Wikimedia Commons", source_url="https://commons.wikimedia.org/wiki/File:education.webm",
        educator_name="陶行知", copyright_status="authorized", access_level="public",
        license_code="CC BY-SA 4.0", license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        media_url="https://upload.wikimedia.org/example.webm", embed_url="https://upload.wikimedia.org/example.webm",
        embed_allowed=True, subtitle_access=True, download_allowed=True, transcription_allowed=True,
    )
    assert collection_service._ingest_candidate(candidate, FakeVideoAdapter()) == "succeeded"
    video = collection_service.list_videos()[0]
    transcript_id = collection_service.import_subtitle(
        video.id, language="zh", origin="official_subtitle", fetch_from_source=False,
        content="WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n尊重学生并持续反思教学。\n\n00:00:04.000 --> 00:00:06.000\n以责任和公正改进教育实践。\n",
    )
    matches = collection_service.search_transcript("反思", 0, 5000)
    assert matches[0]["transcript_id"] == transcript_id
    assert matches[0]["start_ms"] == 1000

    analysis = collection_service.analyze_resource(video.resource_id)
    assert analysis.status == "succeeded"
    assert len(analysis.evidence) == 3
    assert all(item.quote for item in analysis.evidence)
    assert collection_service.list_videos()[0].transcripts[0].model_version == ""


def test_doi_identifier_prevents_duplicate_paper(collection_service: CollectionService) -> None:
    paper = Candidate(
        kind="paper", external_id="10.1000/example", title="Education paper",
        source_name="Crossref", source_url="https://doi.org/10.1000/example",
        identifiers={"doi": "10.1000/example"}, authors=["Researcher"],
    )
    adapter = type("Crossref", (), {"key": "crossref"})()
    assert collection_service._ingest_candidate(paper, adapter) == "succeeded"
    assert collection_service._ingest_candidate(paper, adapter) == "duplicate"
    with collection_service.session_factory() as session:
        assert session.scalar(select(ResourceIdentifier).where(ResourceIdentifier.scheme == "doi")) is not None


def test_pause_and_resume_are_persisted(collection_service: CollectionService) -> None:
    wikidata = next(source for source in collection_service.list_sources() if source.adapter_key == "wikidata")
    job_id = collection_service.create_job(CollectionJobCreate(source_id=wikidata.id, query="蔡元培"))
    collection_service.pause_job(job_id)
    assert collection_service.list_jobs()[0].status == "paused"
    collection_service.resume_job(job_id)
    with collection_service.session_factory() as session:
        assert session.get(CollectionJob, job_id).status == "queued"


def test_manual_source_domain_and_transcription_url_are_restricted(collection_service: CollectionService) -> None:
    cctv = next(source for source in collection_service.list_sources() if source.adapter_key == "cctv_manual")
    with pytest.raises(ValueError, match="域名"):
        collection_service.register_manual_resource(
            source_id=cctv.id, title="伪造来源", source_url="https://example.com/video",
            resource_type="video", educator_name="", description="", restriction_reason="",
        )
    with pytest.raises(ValueError, match="内网"):
        collection_service._require_public_https("https://127.0.0.1/private-media")
