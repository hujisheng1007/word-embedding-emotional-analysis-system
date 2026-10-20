from __future__ import annotations

"""Database-backed orchestration for compliant multi-source collection."""

import hashlib
import ipaddress
import json
import socket
import shutil
import subprocess
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlparse

import httpx
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.collectors import get_adapter, source_definitions
from app.collectors.base import Candidate
from app.collectors.wikidata import WikidataPersonAdapter
from app.db.research_models import (
    CollectionJob, CollectionLog, CollectionSource, EducatorPerson, PersonExternalIdentity,
    PersonFact, PersonalityAnalysisRun, PersonalityEvidence, ResearchResource, ResourceAuthor,
    ResourceIdentifier, ResourceSegment, Transcript, TranscriptCue, VideoAsset,
)
from app.db.session import get_session_factory
from app.schemas.analysis import AnalysisRequest
from app.schemas.collection import (
    AnalysisEvidenceView, CollectionJobCreate, CollectionJobView, CollectionLogView,
    CollectionSourceView, CollectionStats, EducatorPersonView, PersonFactView,
    ResourceAnalysisView, TranscriptCueView, TranscriptView, VideoView,
)
from app.services.analysis_service import AnalysisService
from app.services.resource_parsers import parse_resource


REQUIRED_TABLES = {
    "collection_sources", "collection_jobs", "collection_logs", "resource_identifiers",
    "person_external_identities", "person_facts", "video_assets", "transcripts",
    "transcript_cues", "personality_analysis_runs", "personality_evidence",
}


class CollectionSchemaNotReady(RuntimeError):
    pass


class CollectionService:
    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.analysis_service = AnalysisService()

    def _check_schema(self, session: Session) -> None:
        missing = REQUIRED_TABLES - set(inspect(session.get_bind()).get_table_names())
        if missing:
            raise CollectionSchemaNotReady(
                "多源采集中心尚未初始化，请执行 `alembic upgrade head`。缺少表：" + "、".join(sorted(missing))
            )
    def ensure_sources(self) -> None:
        with self.session_factory() as session:
            self._check_schema(session)
            for definition in source_definitions():
                source = session.scalar(
                    select(CollectionSource).where(CollectionSource.adapter_key == definition["adapter_key"])
                )
                if source is None:
                    session.add(CollectionSource(id=str(uuid4()), **definition))
            session.commit()

    def list_sources(self) -> list[CollectionSourceView]:
        self.ensure_sources()
        with self.session_factory() as session:
            sources = session.scalars(
                select(CollectionSource).order_by(CollectionSource.source_type, CollectionSource.name)
            ).all()
            return [
                CollectionSourceView(**{field: getattr(item, field) for field in CollectionSourceView.model_fields})
                for item in sources
            ]

    def update_schedule(self, source_id: str, interval_minutes: int) -> None:
        with self.session_factory() as session:
            source = session.get(CollectionSource, source_id)
            if source is None:
                raise ValueError("采集来源不存在")
            if interval_minutes and not source.enabled:
                raise ValueError("人工登记来源不能启用自动增量采集")
            source.schedule_interval_minutes = interval_minutes
            source.next_run_at = (
                datetime.utcnow() + timedelta(minutes=interval_minutes) if interval_minutes else None
            )
            session.commit()

    def run_due_jobs(self) -> list[str]:
        now = datetime.utcnow()
        queued: list[str] = []
        self.ensure_sources()
        with self.session_factory() as session:
            sources = session.scalars(select(CollectionSource).where(
                CollectionSource.enabled.is_(True),
                CollectionSource.schedule_interval_minutes > 0,
                CollectionSource.next_run_at <= now,
            )).all()
            for source in sources:
                last_job = session.scalar(select(CollectionJob).where(
                    CollectionJob.source_id == source.id
                ).order_by(CollectionJob.created_at.desc()))
                if last_job is None:
                    source.next_run_at = now + timedelta(minutes=source.schedule_interval_minutes)
                    continue
                job = CollectionJob(
                    id=str(uuid4()), source_id=source.id, job_type=last_job.job_type,
                    query_json=last_job.query_json, status="queued",
                )
                session.add(job)
                queued.append(job.id)
                source.next_run_at = now + timedelta(minutes=source.schedule_interval_minutes)
            session.commit()
        for job_id in queued:
            self.run_job(job_id)
        return queued

    def create_job(self, payload: CollectionJobCreate) -> str:
        self.ensure_sources()
        with self.session_factory() as session:
            source = session.get(CollectionSource, payload.source_id)
            if source is None:
                raise ValueError("采集来源不存在")
            if not source.enabled:
                raise ValueError("该来源当前仅支持人工登记，不能创建自动采集任务")
            job = CollectionJob(
                id=str(uuid4()), source_id=source.id, job_type=f"{source.source_type}_search",
                query_json=json.dumps(payload.model_dump(), ensure_ascii=False), status="queued",
            )
            session.add(job)
            session.commit()
            return job.id

    def _log(
        self, session: Session, job_id: str, level: str, event: str,
        message: str, context: dict[str, Any] | None = None,
    ) -> None:
        session.add(CollectionLog(
            id=str(uuid4()), job_id=job_id, level=level, event=event,
            message=message[:4000], context_json=json.dumps(context or {}, ensure_ascii=False, default=str),
        ))

    def run_job(self, job_id: str) -> None:
        with self.session_factory() as session:
            self._check_schema(session)
            job = session.get(CollectionJob, job_id)
            if job is None or job.status not in {"queued", "paused", "failed"}:
                return
            source = session.get(CollectionSource, job.source_id)
            if source is None:
                return
            query = json.loads(job.query_json)
            job.status = "running"
            job.pause_requested = False
            job.started_at = job.started_at or datetime.utcnow()
            job.completed_at = None
            self._log(session, job.id, "info", "started", f"开始从 {source.name} 检索“{query['query']}”")
            session.commit()
            source_key = source.adapter_key
            rate_delay = min(60 / max(source.rate_limit_per_minute, 1), 3.0)

        try:
            adapter = get_adapter(source_key)
            candidates = adapter.search(
                query["query"], query.get("limit", 10),
                educator_name=query.get("educator_name", ""), language=query.get("language", "zh"),
                email=query.get("contact_email", ""),
            )
            with self.session_factory() as session:
                job = session.get(CollectionJob, job_id)
                assert job is not None
                job.total_count = len(candidates)
                session.commit()

            for index, candidate in enumerate(candidates):
                with self.session_factory() as session:
                    job = session.get(CollectionJob, job_id)
                    assert job is not None
                    if job.pause_requested:
                        job.status = "paused"
                        self._log(session, job.id, "info", "paused", "任务已在条目边界安全暂停")
                        session.commit()
                        return
                try:
                    outcome = self._ingest_candidate(candidate, adapter)
                    with self.session_factory() as session:
                        job = session.get(CollectionJob, job_id)
                        assert job is not None
                        if outcome == "duplicate":
                            job.duplicate_count += 1
                        else:
                            job.success_count += 1
                        self._log(session, job.id, "info", outcome, candidate.title, {"source_url": candidate.source_url})
                        session.commit()
                except Exception as exc:
                    with self.session_factory() as session:
                        job = session.get(CollectionJob, job_id)
                        assert job is not None
                        job.failed_count += 1
                        self._log(session, job.id, "error", "item_failed", str(exc), {"title": candidate.title})
                        session.commit()
                if index + 1 < len(candidates):
                    time.sleep(rate_delay)

            with self.session_factory() as session:
                job = session.get(CollectionJob, job_id)
                assert job is not None
                source = session.get(CollectionSource, job.source_id)
                job.status = "partial" if job.failed_count else "succeeded"
                job.completed_at = datetime.utcnow()
                if source:
                    source.last_run_at = job.completed_at
                    if source.schedule_interval_minutes:
                        source.next_run_at = job.completed_at + timedelta(minutes=source.schedule_interval_minutes)
                self._log(session, job.id, "info", "completed", f"成功 {job.success_count}，重复 {job.duplicate_count}，失败 {job.failed_count}")
                session.commit()
        except Exception as exc:
            with self.session_factory() as session:
                job = session.get(CollectionJob, job_id)
                if job:
                    job.retry_count += 1
                    job.status = "failed"
                    job.error_message = str(exc)[:4000]
                    job.completed_at = datetime.utcnow()
                    self._log(session, job.id, "error", "failed", str(exc))
                    session.commit()

    def _get_or_create_person(self, session: Session, name: str) -> EducatorPerson | None:
        name = name.strip()
        if not name:
            return None
        person = session.scalar(select(EducatorPerson).where(EducatorPerson.display_name == name))
        if person is None:
            person = EducatorPerson(id=str(uuid4()), display_name=name)
            session.add(person)
            session.flush()
        return person

    def _ingest_candidate(self, item: Candidate, adapter: Any) -> str:
        with self.session_factory() as session:
            for scheme, value in item.identifiers.items():
                if value and session.scalar(select(ResourceIdentifier).where(
                    ResourceIdentifier.scheme == scheme, ResourceIdentifier.value == value
                )):
                    return "duplicate"
            if item.source_url and session.scalar(
                select(ResearchResource).where(ResearchResource.source_url == item.source_url)
            ):
                return "duplicate"

            if item.kind == "person":
                identity = session.scalar(select(PersonExternalIdentity).where(
                    PersonExternalIdentity.source_key == adapter.key,
                    PersonExternalIdentity.external_id == item.external_id,
                ))
                if identity:
                    return "duplicate"
                person = self._get_or_create_person(session, item.educator_name or item.title)
                assert person is not None
                raw = item.metadata
                if isinstance(adapter, WikidataPersonAdapter):
                    raw = adapter.entity_facts(item.external_id)
                    person.birth_date = adapter.time_claim(raw, "P569") or person.birth_date
                    person.death_date = adapter.time_claim(raw, "P570") or person.death_date
                    aliases = raw.get("aliases", {}).get("zh", [])
                    person.aliases_json = json.dumps(
                        [row.get("value") for row in aliases if row.get("value")], ensure_ascii=False
                    )
                session.add(PersonExternalIdentity(
                    id=str(uuid4()), person_id=person.id, source_key=adapter.key,
                    external_id=item.external_id, canonical_url=item.source_url,
                    confidence=1.0, review_status="pending",
                    raw_json=json.dumps(raw, ensure_ascii=False, default=str),
                ))
                if item.description:
                    digest = hashlib.sha256(item.description.encode()).hexdigest()
                    exists = session.scalar(select(PersonFact).where(
                        PersonFact.person_id == person.id, PersonFact.content_sha256 == digest
                    ))
                    if not exists:
                        session.add(PersonFact(
                            id=str(uuid4()), person_id=person.id, fact_type="source_description",
                            value_text=item.description, source_url=item.source_url,
                            source_title=item.title, source_publisher=item.source_name,
                            review_status="pending", extracted_by=adapter.key, content_sha256=digest,
                        ))
                session.commit()
                return "succeeded"

            person = self._get_or_create_person(session, item.educator_name)
            resource = ResearchResource(
                id=str(uuid4()), title=item.title[:500], resource_type=item.kind,
                source_institution=item.source_name[:255], source_url=item.source_url,
                publication_date=item.publication_date, file_format="",
                copyright_status=item.copyright_status, fulltext_allowed=False,
                access_level=item.access_level, original_locator=item.source_url,
                extracted_text="", educator=person, analysis_status="pending", data_version="1",
                citation_text=f"{item.title}. {item.source_name}. {item.source_url}",
                content_sha256=hashlib.sha256((item.source_url or item.external_id).encode()).hexdigest(),
            )
            session.add(resource)
            session.flush()
            for name in dict.fromkeys(item.authors):
                session.add(ResourceAuthor(
                    id=str(uuid4()), resource_id=resource.id, name=name[:255], role="author"
                ))
            for scheme, value in item.identifiers.items():
                if value:
                    session.add(ResourceIdentifier(
                        id=str(uuid4()), resource_id=resource.id, scheme=scheme, value=value
                    ))
            if item.kind == "video":
                session.add(VideoAsset(
                    id=str(uuid4()), resource_id=resource.id, platform=adapter.key,
                    external_id=item.external_id, page_url=item.source_url,
                    embed_url=item.embed_url, media_url=item.media_url,
                    duration_seconds=item.duration_seconds, description=item.description,
                    license_code=item.license_code, license_url=item.license_url,
                    embed_allowed=item.embed_allowed, subtitle_access=item.subtitle_access,
                    download_allowed=item.download_allowed,
                    transcription_allowed=item.transcription_allowed,
                    restriction_reason=item.restriction_reason,
                    metadata_json=json.dumps(item.metadata, ensure_ascii=False, default=str),
                ))
            session.commit()
            return "succeeded"

    def pause_job(self, job_id: str) -> None:
        with self.session_factory() as session:
            job = session.get(CollectionJob, job_id)
            if not job:
                raise ValueError("任务不存在")
            if job.status == "running":
                job.pause_requested = True
            elif job.status == "queued":
                job.status = "paused"
            session.commit()

    def resume_job(self, job_id: str) -> None:
        with self.session_factory() as session:
            job = session.get(CollectionJob, job_id)
            if not job:
                raise ValueError("任务不存在")
            if job.status not in {"paused", "failed"}:
                raise ValueError("只有暂停或失败的任务可以恢复")
            job.status = "queued"
            job.pause_requested = False
            job.error_message = ""
            session.commit()

    def list_jobs(self, limit: int = 50) -> list[CollectionJobView]:
        self.ensure_sources()
        with self.session_factory() as session:
            rows = session.execute(
                select(CollectionJob, CollectionSource.name).join(CollectionSource)
                .order_by(CollectionJob.created_at.desc()).limit(limit)
            ).all()
            result = []
            for job, source_name in rows:
                query = json.loads(job.query_json)
                result.append(CollectionJobView(
                    id=job.id, source_id=job.source_id, source_name=source_name,
                    job_type=job.job_type, query=query.get("query", ""), status=job.status,
                    total_count=job.total_count, success_count=job.success_count,
                    failed_count=job.failed_count, duplicate_count=job.duplicate_count,
                    retry_count=job.retry_count, error_message=job.error_message,
                    created_at=job.created_at, started_at=job.started_at,
                    completed_at=job.completed_at,
                ))
            return result

    def list_logs(self, job_id: str) -> list[CollectionLogView]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(CollectionLog).where(CollectionLog.job_id == job_id)
                .order_by(CollectionLog.created_at)
            ).all()
            return [CollectionLogView(
                id=row.id, level=row.level, event=row.event, message=row.message,
                context=json.loads(row.context_json), created_at=row.created_at,
            ) for row in rows]

    def get_stats(self) -> CollectionStats:
        self.ensure_sources()
        with self.session_factory() as session:
            def count(model: Any, clause: Any | None = None) -> int:
                statement = select(func.count()).select_from(model)
                if clause is not None:
                    statement = statement.where(clause)
                return int(session.scalar(statement) or 0)
            return CollectionStats(
                source_count=count(CollectionSource), job_count=count(CollectionJob),
                running_count=count(CollectionJob, CollectionJob.status.in_(["queued", "running", "paused"])),
                success_count=int(session.scalar(select(func.coalesce(func.sum(CollectionJob.success_count), 0))) or 0),
                failed_count=int(session.scalar(select(func.coalesce(func.sum(CollectionJob.failed_count), 0))) or 0),
                duplicate_count=int(session.scalar(select(func.coalesce(func.sum(CollectionJob.duplicate_count), 0))) or 0),
                person_count=count(EducatorPerson), video_count=count(VideoAsset),
                transcript_count=count(Transcript),
                paper_count=count(ResearchResource, ResearchResource.resource_type == "paper"),
            )

    def list_people(self, keyword: str = "") -> list[EducatorPersonView]:
        with self.session_factory() as session:
            statement = select(EducatorPerson).order_by(EducatorPerson.display_name)
            if keyword.strip():
                statement = statement.where(EducatorPerson.display_name.contains(keyword.strip()))
            people = session.scalars(statement.limit(100)).all()
            output: list[EducatorPersonView] = []
            for person in people:
                identities = session.scalars(select(PersonExternalIdentity).where(
                    PersonExternalIdentity.person_id == person.id
                )).all()
                facts = session.scalars(select(PersonFact).where(
                    PersonFact.person_id == person.id
                ).order_by(PersonFact.created_at)).all()
                resource_count = int(session.scalar(select(func.count()).select_from(ResearchResource).where(
                    ResearchResource.educator_person_id == person.id
                )) or 0)
                output.append(EducatorPersonView(
                    id=person.id, display_name=person.display_name,
                    aliases=json.loads(person.aliases_json or "[]"),
                    birth_date=person.birth_date.isoformat() if person.birth_date else None,
                    death_date=person.death_date.isoformat() if person.death_date else None,
                    identities=[{
                        "id": row.id, "source_key": row.source_key, "external_id": row.external_id,
                        "canonical_url": row.canonical_url, "confidence": row.confidence,
                        "review_status": row.review_status,
                    } for row in identities],
                    facts=[PersonFactView(
                        id=row.id, fact_type=row.fact_type, value_text=row.value_text,
                        source_url=row.source_url, source_title=row.source_title,
                        source_publisher=row.source_publisher, review_status=row.review_status,
                    ) for row in facts],
                    resource_count=resource_count,
                ))
            return output

    def review_fact(self, fact_id: str, status: str, corrected_text: str = "") -> None:
        with self.session_factory() as session:
            fact = session.get(PersonFact, fact_id)
            if fact is None:
                raise ValueError("人物事实不存在")
            if status == "corrected":
                if not corrected_text.strip():
                    raise ValueError("纠错状态必须填写修订文本")
                fact.value_text = corrected_text.strip()
                fact.content_sha256 = hashlib.sha256(fact.value_text.encode()).hexdigest()
            fact.review_status = status
            session.commit()

    def review_identity(self, identity_id: str, status: str) -> None:
        with self.session_factory() as session:
            identity = session.get(PersonExternalIdentity, identity_id)
            if identity is None:
                raise ValueError("人物身份记录不存在")
            identity.review_status = status
            session.commit()

    def list_videos(self, keyword: str = "") -> list[VideoView]:
        with self.session_factory() as session:
            statement = select(VideoAsset, ResearchResource, EducatorPerson).join(
                ResearchResource, VideoAsset.resource_id == ResearchResource.id
            ).outerjoin(EducatorPerson, ResearchResource.educator_person_id == EducatorPerson.id)
            if keyword.strip():
                term = f"%{keyword.strip()}%"
                statement = statement.where(
                    (ResearchResource.title.like(term)) | (EducatorPerson.display_name.like(term))
                )
            rows = session.execute(statement.order_by(VideoAsset.collected_at.desc()).limit(100)).all()
            output: list[VideoView] = []
            for video, resource, person in rows:
                transcripts = session.scalars(select(Transcript).where(
                    Transcript.video_asset_id == video.id
                ).order_by(Transcript.created_at.desc())).all()
                transcript_views: list[TranscriptView] = []
                for transcript in transcripts:
                    cues = session.scalars(select(TranscriptCue).where(
                        TranscriptCue.transcript_id == transcript.id
                    ).order_by(TranscriptCue.sequence)).all()
                    transcript_views.append(TranscriptView(
                        id=transcript.id, resource_id=transcript.resource_id,
                        language=transcript.language, origin=transcript.origin,
                        model_name=transcript.model_name, model_version=transcript.model_version,
                        review_status=transcript.review_status,
                        cues=[TranscriptCueView(
                            id=cue.id, sequence=cue.sequence, start_ms=cue.start_ms,
                            end_ms=cue.end_ms, text=cue.text, review_status=cue.review_status,
                        ) for cue in cues],
                    ))
                output.append(VideoView(
                    id=video.id, resource_id=resource.id, title=resource.title,
                    educator_name=person.display_name if person else "", page_url=video.page_url,
                    embed_url=video.embed_url, media_url=video.media_url,
                    license_code=video.license_code, license_url=video.license_url,
                    embed_allowed=video.embed_allowed, subtitle_access=video.subtitle_access,
                    download_allowed=video.download_allowed,
                    transcription_allowed=video.transcription_allowed,
                    restriction_reason=video.restriction_reason, transcripts=transcript_views,
                ))
            return output

    @staticmethod
    def _time_to_ms(value: str) -> int:
        normalized = value.replace(",", ".")
        parts = normalized.split(":")
        if len(parts) == 2:
            hours, minutes, seconds = 0, int(parts[0]), float(parts[1])
        else:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
        return int(((hours * 60 + minutes) * 60 + seconds) * 1000)

    def import_subtitle(
        self, video_id: str, *, language: str, origin: str, content: str,
        fetch_from_source: bool, model_name: str = "", model_version: str = "",
    ) -> str:
        with self.session_factory() as session:
            video = session.get(VideoAsset, video_id)
            if video is None:
                raise ValueError("视频记录不存在")
            if fetch_from_source:
                if not video.subtitle_access:
                    raise ValueError("该来源未声明可访问字幕")
                content = get_adapter(video.platform).fetch_subtitle(video.external_id, language)
            if not content.strip():
                raise ValueError("字幕内容不能为空")
            if origin == "authorized_asr" and not video.transcription_allowed:
                raise ValueError("该视频没有可记录的转写授权")
            parsed = parse_resource("subtitle.vtt", content.encode("utf-8"))
            transcript = Transcript(
                id=str(uuid4()), resource_id=video.resource_id, video_asset_id=video.id,
                language=language, origin=origin, model_name=model_name,
                model_version=model_version, review_status="pending",
                full_text="\n".join(item.text for item in parsed),
            )
            session.add(transcript)
            resource = session.get(ResearchResource, video.resource_id)
            assert resource is not None
            resource.extracted_text = transcript.full_text
            resource.analysis_status = "pending"
            start_ordinal = int(session.scalar(select(func.coalesce(func.max(ResourceSegment.ordinal), 0)).where(
                ResourceSegment.resource_id == resource.id
            )) or 0)
            for sequence, item in enumerate(parsed, 1):
                start, end = item.locator_value.split("-->", 1)
                cue = TranscriptCue(
                    id=str(uuid4()), transcript_id=transcript.id, sequence=sequence,
                    start_ms=self._time_to_ms(start), end_ms=self._time_to_ms(end),
                    text=item.text, review_status="pending",
                )
                session.add(cue)
                session.add(ResourceSegment(
                    id=str(uuid4()), resource_id=resource.id, ordinal=start_ordinal + sequence,
                    locator_type="timestamp", locator_value=item.locator_value,
                    text=item.text, text_sha256=hashlib.sha256(item.text.encode()).hexdigest(),
                ))
            session.commit()
            return transcript.id

    def create_transcription_job(self, video_id: str, language: str, model_name: str) -> str:
        with self.session_factory() as session:
            video = session.get(VideoAsset, video_id)
            if video is None:
                raise ValueError("视频记录不存在")
            if not (video.download_allowed and video.transcription_allowed and video.media_url):
                raise ValueError("该视频未同时获得媒体下载与转写许可")
            source = session.scalar(select(CollectionSource).where(
                CollectionSource.adapter_key == video.platform
            ))
            if source is None:
                raise ValueError("视频来源配置不存在")
            job = CollectionJob(
                id=str(uuid4()), source_id=source.id, job_type="video_transcription",
                query_json=json.dumps({
                    "video_id": video_id, "language": language, "model_name": model_name,
                }, ensure_ascii=False), status="queued", total_count=1,
            )
            session.add(job)
            session.commit()
            return job.id

    @staticmethod
    def _require_public_https(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("远程媒体必须使用有效的 HTTPS URL")
        try:
            addresses = {
                entry[4][0] for entry in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            raise ValueError("媒体主机无法解析") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise ValueError("拒绝访问内网、回环或保留地址上的媒体")

    def run_transcription_job(self, job_id: str) -> None:
        with self.session_factory() as session:
            job = session.get(CollectionJob, job_id)
            if job is None or job.job_type != "video_transcription":
                return
            query = json.loads(job.query_json)
            video = session.get(VideoAsset, query["video_id"])
            if video is None:
                return
            job.status = "running"
            job.started_at = datetime.utcnow()
            self._log(session, job.id, "info", "started", "开始下载已授权媒体并执行 Whisper 转写")
            session.commit()
            media_url = video.media_url

        try:
            self._require_public_https(media_url)
            whisper = shutil.which("whisper")
            if not whisper:
                raise RuntimeError("未安装 Whisper CLI；请安装 openai-whisper 并确认 ffmpeg 可用")
            try:
                whisper_version = version("openai-whisper")
            except PackageNotFoundError:
                whisper_version = "cli-unknown"
            with tempfile.TemporaryDirectory(prefix="educator-transcribe-") as folder:
                media_path = Path(folder) / "authorized-media"
                byte_count = 0
                with httpx.stream("GET", media_url, follow_redirects=True, timeout=60) as response:
                    response.raise_for_status()
                    with media_path.open("wb") as output:
                        for chunk in response.iter_bytes():
                            byte_count += len(chunk)
                            if byte_count > 500 * 1024 * 1024:
                                raise ValueError("授权媒体超过 500 MB 转写上限")
                            output.write(chunk)
                command = [
                    whisper, str(media_path), "--model", query["model_name"],
                    "--language", query["language"], "--output_format", "vtt",
                    "--output_dir", folder,
                ]
                completed = subprocess.run(command, capture_output=True, text=True, timeout=6 * 60 * 60)
                if completed.returncode != 0:
                    raise RuntimeError((completed.stderr or completed.stdout)[-3000:])
                vtt_files = list(Path(folder).glob("*.vtt"))
                if not vtt_files:
                    raise RuntimeError("Whisper 未生成 VTT 结果")
                content = vtt_files[0].read_text(encoding="utf-8")
                self.import_subtitle(
                    query["video_id"], language=query["language"], origin="authorized_asr",
                    content=content, fetch_from_source=False,
                    model_name=query["model_name"], model_version=whisper_version,
                )
            with self.session_factory() as session:
                job = session.get(CollectionJob, job_id)
                assert job is not None
                job.status = "succeeded"
                job.success_count = 1
                job.completed_at = datetime.utcnow()
                self._log(session, job.id, "info", "completed", "Whisper 转写完成并已入库，等待人工审核")
                session.commit()
        except Exception as exc:
            with self.session_factory() as session:
                job = session.get(CollectionJob, job_id)
                if job:
                    job.status = "failed"
                    job.failed_count = 1
                    job.error_message = str(exc)[:4000]
                    job.completed_at = datetime.utcnow()
                    self._log(session, job.id, "error", "failed", str(exc))
                    session.commit()

    def review_cue(self, cue_id: str, status: str, corrected_text: str = "") -> None:
        with self.session_factory() as session:
            cue = session.get(TranscriptCue, cue_id)
            if cue is None:
                raise ValueError("字幕片段不存在")
            if status == "corrected":
                if not corrected_text.strip():
                    raise ValueError("纠错状态必须填写修订文本")
                cue.text = corrected_text.strip()
            cue.review_status = status
            transcript = session.get(Transcript, cue.transcript_id)
            if transcript:
                cues = session.scalars(select(TranscriptCue).where(
                    TranscriptCue.transcript_id == transcript.id
                ).order_by(TranscriptCue.sequence)).all()
                transcript.full_text = "\n".join(item.text for item in cues)
            session.commit()

    def search_transcript(self, query: str, start_ms: int | None = None, end_ms: int | None = None) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement = select(TranscriptCue, Transcript, ResearchResource).join(
                Transcript, TranscriptCue.transcript_id == Transcript.id
            ).join(ResearchResource, Transcript.resource_id == ResearchResource.id)
            if query.strip():
                statement = statement.where(TranscriptCue.text.contains(query.strip()))
            if start_ms is not None:
                statement = statement.where(TranscriptCue.end_ms >= start_ms)
            if end_ms is not None:
                statement = statement.where(TranscriptCue.start_ms <= end_ms)
            rows = session.execute(statement.order_by(TranscriptCue.start_ms).limit(200)).all()
            return [{
                "cue_id": cue.id, "transcript_id": transcript.id, "resource_id": resource.id,
                "title": resource.title, "start_ms": cue.start_ms, "end_ms": cue.end_ms,
                "text": cue.text, "review_status": cue.review_status,
            } for cue, transcript, resource in rows]

    def register_manual_resource(
        self, *, source_id: str, title: str, source_url: str, resource_type: str,
        educator_name: str, description: str, restriction_reason: str,
    ) -> str:
        self.ensure_sources()
        with self.session_factory() as session:
            source = session.get(CollectionSource, source_id)
            if source is None:
                raise ValueError("采集来源不存在")
            if not source.allows_metadata:
                raise ValueError("该来源未允许登记元数据")
            source_host = (urlparse(source.base_url).hostname or "").lower()
            resource_host = (urlparse(source_url).hostname or "").lower()
            if not source_host or not resource_host or not (
                resource_host == source_host or resource_host.endswith("." + source_host)
                or source_host.endswith("." + resource_host)
            ):
                raise ValueError("资源 URL 域名与所选来源不一致")
            existing = session.scalar(select(ResearchResource).where(ResearchResource.source_url == source_url))
            if existing:
                return existing.id
            person = self._get_or_create_person(session, educator_name)
            resource = ResearchResource(
                id=str(uuid4()), title=title, resource_type=resource_type,
                source_institution=source.name, source_url=source_url, file_format="",
                copyright_status="unknown", fulltext_allowed=False, access_level="public",
                original_locator=source_url, extracted_text="", educator=person,
                analysis_status="pending", data_version="1",
                citation_text=f"{title}. {source.name}. {source_url}",
                content_sha256=hashlib.sha256(source_url.encode()).hexdigest(),
            )
            session.add(resource)
            session.flush()
            if resource_type == "video":
                session.add(VideoAsset(
                    id=str(uuid4()), resource_id=resource.id, platform=source.adapter_key,
                    external_id=source_url, page_url=source_url, description=description,
                    license_code="unknown", embed_allowed=False, subtitle_access=False,
                    download_allowed=False, transcription_allowed=False,
                    restriction_reason=restriction_reason,
                    metadata_json=json.dumps({"manual_registration": True}, ensure_ascii=False),
                ))
            session.commit()
            return resource.id

    def analyze_resource(self, resource_id: str) -> ResourceAnalysisView:
        with self.session_factory() as session:
            resource = session.get(ResearchResource, resource_id)
            if resource is None:
                raise ValueError("研究资源不存在")
            text = resource.extracted_text.strip()
            if not text:
                raise ValueError("资源没有可分析的合法全文或文字稿")
            transcript = session.scalar(select(Transcript).where(
                Transcript.resource_id == resource_id
            ).order_by(Transcript.created_at.desc()))
            cues = session.scalars(select(TranscriptCue).where(
                TranscriptCue.transcript_id == transcript.id
            ).order_by(TranscriptCue.sequence)).all() if transcript else []

        result = self.analysis_service.analyze_text(AnalysisRequest(text=text, mode="hybrid"))
        result_payload = result.model_dump()
        with self.session_factory() as session:
            run = PersonalityAnalysisRun(
                id=str(uuid4()), resource_id=resource_id,
                transcript_id=transcript.id if transcript else None,
                engine_version="triple-personality-v2", status="succeeded",
                result_json=json.dumps(result_payload, ensure_ascii=False, default=str),
            )
            session.add(run)
            evidence_views: list[AnalysisEvidenceView] = []
            for dimension in result.dimension_scores:
                matching_cue = None
                for cue in cues:
                    if any(keyword in cue.text for keyword in dimension.matched_keywords):
                        matching_cue = cue
                        break
                quote = matching_cue.text if matching_cue else (text[:300] if text else "")
                locator_type = "timestamp" if matching_cue else "text_excerpt"
                locator_value = str(matching_cue.start_ms) if matching_cue else "0"
                evidence = PersonalityEvidence(
                    id=str(uuid4()), analysis_run_id=run.id, resource_id=resource_id,
                    transcript_cue_id=matching_cue.id if matching_cue else None,
                    dimension_id=dimension.id, dimension_name=dimension.name,
                    score=dimension.score, quote=quote, locator_type=locator_type,
                    locator_value=locator_value, review_status="pending",
                )
                session.add(evidence)
                evidence_views.append(AnalysisEvidenceView(
                    id=evidence.id, dimension_id=evidence.dimension_id,
                    dimension_name=evidence.dimension_name, score=evidence.score,
                    quote=evidence.quote, locator_type=evidence.locator_type,
                    locator_value=evidence.locator_value, review_status=evidence.review_status,
                ))
            resource = session.get(ResearchResource, resource_id)
            assert resource is not None
            resource.analysis_status = "completed"
            session.commit()
            return ResourceAnalysisView(
                run_id=run.id, resource_id=resource_id, status=run.status,
                engine_version=run.engine_version, result=result_payload, evidence=evidence_views,
            )

    def get_latest_analysis(self, resource_id: str) -> ResourceAnalysisView | None:
        with self.session_factory() as session:
            run = session.scalar(select(PersonalityAnalysisRun).where(
                PersonalityAnalysisRun.resource_id == resource_id
            ).order_by(PersonalityAnalysisRun.created_at.desc()))
            if run is None:
                return None
            evidence = session.scalars(select(PersonalityEvidence).where(
                PersonalityEvidence.analysis_run_id == run.id
            )).all()
            return ResourceAnalysisView(
                run_id=run.id, resource_id=resource_id, status=run.status,
                engine_version=run.engine_version, result=json.loads(run.result_json),
                evidence=[AnalysisEvidenceView(
                    id=row.id, dimension_id=row.dimension_id,
                    dimension_name=row.dimension_name, score=row.score,
                    quote=row.quote, locator_type=row.locator_type,
                    locator_value=row.locator_value, review_status=row.review_status,
                ) for row in evidence],
            )
