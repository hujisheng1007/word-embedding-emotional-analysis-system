from __future__ import annotations

import hashlib
import os
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func, inspect, or_, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.db.research_models import (
    EducatorPerson,
    ResearchResource,
    ResourceAuthor,
    ResourceFile,
    ResourceImportJob,
    ResourceSegment,
)
from app.db.session import get_session_factory
from app.schemas.research_resources import (
    ResearchResourceDetail,
    ResearchResourceListResponse,
    ResearchResourceStats,
    ResearchResourceSummary,
    ResourceAuthorView,
    ResourceFileView,
    ResourceImportJobView,
    ResourceImportResult,
    ResourceSegmentView,
)
from app.services.resource_parsers import ALLOWED_EXTENSIONS, ResourceParseError, parse_resource


MAX_UPLOAD_BYTES = 25 * 1024 * 1024
RESOURCE_TYPES = {"book", "interview", "paper", "video_subtitle", "webpage", "policy", "note", "other"}
COPYRIGHT_STATUSES = {"unknown", "authorized", "public_domain", "fair_use", "restricted"}
ACCESS_LEVELS = {"restricted", "internal", "public"}
REQUIRED_TABLES = {
    "educator_persons",
    "research_resources",
    "resource_authors",
    "resource_files",
    "resource_segments",
    "resource_import_jobs",
}


class ResourceSchemaNotReady(RuntimeError):
    pass


class ResourceImportError(ValueError):
    pass


class ResearchResourceService:
    def __init__(
        self,
        session_factory: sessionmaker | None = None,
        storage_root: Path | None = None,
    ) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.storage_root = storage_root or Path(__file__).resolve().parents[2] / "runtime" / "research_resources"

    def _check_schema(self, session: Session) -> None:
        existing = set(inspect(session.get_bind()).get_table_names())
        missing = sorted(REQUIRED_TABLES - existing)
        if missing:
            raise ResourceSchemaNotReady(
                "研究资源库尚未初始化，请先执行 `alembic upgrade head`。缺少表：" + "、".join(missing)
            )

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename.replace("\\", "/")).name.strip()
        if not name or name in {".", ".."}:
            raise ResourceImportError("文件名无效")
        return name[:500]

    @staticmethod
    def _validate_metadata(metadata: dict[str, Any]) -> None:
        if metadata.get("resource_type", "other") not in RESOURCE_TYPES:
            raise ResourceImportError("资源类型不在允许范围内")
        if metadata.get("copyright_status", "unknown") not in COPYRIGHT_STATUSES:
            raise ResourceImportError("版权状态不在允许范围内")
        if metadata.get("access_level", "restricted") not in ACCESS_LEVELS:
            raise ResourceImportError("访问级别不在允许范围内")
        if metadata.get("fulltext_allowed") and metadata.get("copyright_status") == "restricted":
            raise ResourceImportError("版权状态为 restricted 时不能保存全文")

    def _persist_failed_job(self, job_id: str, message: str) -> None:
        with self.session_factory() as session:
            job = session.get(ResourceImportJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = message[:2000]
                job.completed_at = datetime.utcnow()
                session.commit()

    def import_file(
        self,
        *,
        filename: str,
        data: bytes,
        media_type: str = "",
        title: str = "",
        resource_type: str = "other",
        authors: list[str] | None = None,
        educator_name: str = "",
        source_institution: str = "",
        source_url: str = "",
        publication_date: date | None = None,
        copyright_status: str = "unknown",
        fulltext_allowed: bool = False,
        access_level: str = "restricted",
        data_version: str = "1",
        citation_text: str = "",
    ) -> ResourceImportResult:
        safe_name = self._safe_filename(filename)
        extension = Path(safe_name).suffix.lower()
        metadata = {
            "resource_type": resource_type,
            "copyright_status": copyright_status,
            "access_level": access_level,
            "fulltext_allowed": fulltext_allowed,
        }
        digest = hashlib.sha256(data).hexdigest()
        job_id = str(uuid4())

        with self.session_factory() as session:
            self._check_schema(session)
            session.add(
                ResourceImportJob(
                    id=job_id,
                    file_name=safe_name,
                    file_sha256=digest,
                    status="running",
                    started_at=datetime.utcnow(),
                )
            )
            session.commit()

        try:
            if extension not in ALLOWED_EXTENSIONS:
                raise ResourceImportError(f"不支持的文件格式：{extension or '无扩展名'}")
            if not data:
                raise ResourceImportError("文件为空")
            if len(data) > MAX_UPLOAD_BYTES:
                raise ResourceImportError(f"文件超过 {MAX_UPLOAD_BYTES // 1024 // 1024} MB 限制")
            self._validate_metadata(metadata)

            with self.session_factory() as session:
                duplicate_file = session.scalar(select(ResourceFile).where(ResourceFile.sha256 == digest))
                if duplicate_file:
                    job = session.get(ResourceImportJob, job_id)
                    assert job is not None
                    job.status = "duplicate"
                    job.resource_id = duplicate_file.resource_id
                    job.duplicate_of_resource_id = duplicate_file.resource_id
                    job.completed_at = datetime.utcnow()
                    session.commit()
                    return ResourceImportResult(
                        job_id=job_id,
                        file_name=safe_name,
                        status="duplicate",
                        resource_id=duplicate_file.resource_id,
                        duplicate_of_resource_id=duplicate_file.resource_id,
                    )

            parsed_segments = parse_resource(safe_name, data) if fulltext_allowed else []
            resource_id = str(uuid4())
            resource_file_id = str(uuid4())
            stored_name = ""
            stored_path = ""
            final_path: Path | None = None

            if fulltext_allowed:
                stored_name = f"{digest[:16]}{extension}"
                resource_dir = self.storage_root / resource_id
                resource_dir.mkdir(parents=True, exist_ok=True)
                final_path = resource_dir / stored_name
                temporary_path = resource_dir / f".{stored_name}.{uuid4().hex}.tmp"
                temporary_path.write_bytes(data)
                os.replace(temporary_path, final_path)
                stored_path = str(final_path.resolve())

            with self.session_factory() as session:
                try:
                    educator: EducatorPerson | None = None
                    normalized_educator = educator_name.strip()
                    if normalized_educator:
                        educator = session.scalar(
                            select(EducatorPerson).where(EducatorPerson.display_name == normalized_educator)
                        )
                        if educator is None:
                            educator = EducatorPerson(id=str(uuid4()), display_name=normalized_educator)
                            session.add(educator)

                    clean_title = title.strip() or Path(safe_name).stem
                    resource = ResearchResource(
                        id=resource_id,
                        title=clean_title[:500],
                        resource_type=resource_type,
                        source_institution=source_institution.strip()[:255],
                        source_url=source_url.strip(),
                        publication_date=publication_date,
                        file_format=extension.lstrip("."),
                        copyright_status=copyright_status,
                        fulltext_allowed=fulltext_allowed,
                        access_level=access_level,
                        original_locator=source_url.strip() or safe_name,
                        extracted_text="\n\n".join(segment.text for segment in parsed_segments),
                        educator=educator,
                        analysis_status="pending",
                        data_version=(data_version.strip() or "1")[:64],
                        citation_text=citation_text.strip(),
                        content_sha256=digest,
                    )
                    session.add(resource)
                    for author_name in dict.fromkeys(name.strip() for name in (authors or []) if name.strip()):
                        resource.authors.append(
                            ResourceAuthor(id=str(uuid4()), name=author_name[:255], role="author")
                        )
                    resource_file = ResourceFile(
                        id=resource_file_id,
                        original_name=safe_name,
                        stored_name=stored_name,
                        stored_path=stored_path,
                        media_type=media_type[:255],
                        extension=extension.lstrip("."),
                        byte_size=len(data),
                        sha256=digest,
                        parse_status="parsed" if fulltext_allowed else "metadata_only",
                    )
                    resource.files.append(resource_file)
                    for ordinal, segment in enumerate(parsed_segments, 1):
                        resource.segments.append(
                            ResourceSegment(
                                id=str(uuid4()),
                                resource_file=resource_file,
                                ordinal=ordinal,
                                locator_type=segment.locator_type,
                                locator_value=segment.locator_value[:255],
                                text=segment.text,
                                text_sha256=hashlib.sha256(segment.text.encode("utf-8")).hexdigest(),
                            )
                        )
                    job = session.get(ResourceImportJob, job_id)
                    assert job is not None
                    job.status = "succeeded"
                    job.resource = resource
                    job.completed_at = datetime.utcnow()
                    session.commit()
                except Exception:
                    session.rollback()
                    if final_path and final_path.exists():
                        final_path.unlink()
                        try:
                            final_path.parent.rmdir()
                        except OSError:
                            pass
                    raise

            return ResourceImportResult(
                job_id=job_id,
                file_name=safe_name,
                status="succeeded",
                resource_id=resource_id,
                segment_count=len(parsed_segments),
            )
        except (ResourceParseError, ResourceImportError) as exc:
            self._persist_failed_job(job_id, str(exc))
            return ResourceImportResult(job_id=job_id, file_name=safe_name, status="failed", error_message=str(exc))
        except Exception as exc:
            self._persist_failed_job(job_id, f"导入失败：{exc}")
            return ResourceImportResult(
                job_id=job_id,
                file_name=safe_name,
                status="failed",
                error_message=f"导入失败：{exc}",
            )

    @staticmethod
    def _to_summary(resource: ResearchResource) -> ResearchResourceSummary:
        return ResearchResourceSummary(
            id=resource.id,
            title=resource.title,
            resource_type=resource.resource_type,
            source_institution=resource.source_institution,
            source_url=resource.source_url,
            publication_date=resource.publication_date,
            collected_at=resource.collected_at,
            file_format=resource.file_format,
            copyright_status=resource.copyright_status,
            fulltext_allowed=resource.fulltext_allowed,
            access_level=resource.access_level,
            educator_name=resource.educator.display_name if resource.educator else "",
            author_names=[author.name for author in resource.authors],
            analysis_status=resource.analysis_status,
            data_version=resource.data_version,
            segment_count=len(resource.segments),
            updated_at=resource.updated_at,
        )

    def list_resources(
        self,
        *,
        keyword: str = "",
        resource_type: str = "",
        educator_name: str = "",
        analysis_status: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> ResearchResourceListResponse:
        with self.session_factory() as session:
            self._check_schema(session)
            filters = []
            if keyword.strip():
                pattern = f"%{keyword.strip()}%"
                filters.append(
                    or_(
                        ResearchResource.title.ilike(pattern),
                        ResearchResource.source_institution.ilike(pattern),
                        ResearchResource.citation_text.ilike(pattern),
                    )
                )
            if resource_type:
                filters.append(ResearchResource.resource_type == resource_type)
            if analysis_status:
                filters.append(ResearchResource.analysis_status == analysis_status)
            if educator_name.strip():
                filters.append(EducatorPerson.display_name.ilike(f"%{educator_name.strip()}%"))

            count_statement = select(func.count(ResearchResource.id)).outerjoin(ResearchResource.educator).where(*filters)
            total = session.scalar(count_statement) or 0
            statement = (
                select(ResearchResource)
                .outerjoin(ResearchResource.educator)
                .where(*filters)
                .options(
                    selectinload(ResearchResource.educator),
                    selectinload(ResearchResource.authors),
                    selectinload(ResearchResource.segments),
                )
                .order_by(ResearchResource.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            resources = session.scalars(statement).all()
            return ResearchResourceListResponse(
                items=[self._to_summary(resource) for resource in resources],
                total=total,
                limit=limit,
                offset=offset,
            )

    def get_resource(self, resource_id: str) -> ResearchResourceDetail | None:
        with self.session_factory() as session:
            self._check_schema(session)
            resource = session.scalar(
                select(ResearchResource)
                .where(ResearchResource.id == resource_id)
                .options(
                    selectinload(ResearchResource.educator),
                    selectinload(ResearchResource.authors),
                    selectinload(ResearchResource.files),
                    selectinload(ResearchResource.segments),
                )
            )
            if resource is None:
                return None
            summary = self._to_summary(resource).model_dump()
            return ResearchResourceDetail(
                **summary,
                original_locator=resource.original_locator,
                extracted_text=resource.extracted_text,
                citation_text=resource.citation_text,
                content_sha256=resource.content_sha256,
                authors=[
                    ResourceAuthorView(name=item.name, role=item.role, organization=item.organization)
                    for item in resource.authors
                ],
                files=[
                    ResourceFileView(
                        id=item.id,
                        original_name=item.original_name,
                        media_type=item.media_type,
                        extension=item.extension,
                        byte_size=item.byte_size,
                        sha256=item.sha256,
                        parse_status=item.parse_status,
                        error_message=item.error_message,
                        original_retained=bool(item.stored_path),
                    )
                    for item in resource.files
                ],
                segments=[
                    ResourceSegmentView(
                        id=item.id,
                        ordinal=item.ordinal,
                        locator_type=item.locator_type,
                        locator_value=item.locator_value,
                        text=item.text,
                        text_sha256=item.text_sha256,
                    )
                    for item in sorted(resource.segments, key=lambda value: value.ordinal)
                ],
            )

    def get_stats(self) -> ResearchResourceStats:
        with self.session_factory() as session:
            self._check_schema(session)
            rows = session.execute(
                select(
                    ResearchResource.resource_type,
                    ResearchResource.analysis_status,
                    ResearchResource.copyright_status,
                    ResearchResource.fulltext_allowed,
                    ResearchResource.access_level,
                )
            ).all()
            return ResearchResourceStats(
                total=len(rows),
                fulltext_total=sum(1 for row in rows if row.fulltext_allowed),
                restricted_total=sum(1 for row in rows if row.access_level == "restricted"),
                type_counts=dict(Counter(row.resource_type for row in rows)),
                analysis_status_counts=dict(Counter(row.analysis_status for row in rows)),
                copyright_status_counts=dict(Counter(row.copyright_status for row in rows)),
            )

    def list_jobs(self, limit: int = 50) -> list[ResourceImportJobView]:
        with self.session_factory() as session:
            self._check_schema(session)
            jobs = session.scalars(
                select(ResourceImportJob).order_by(ResourceImportJob.started_at.desc()).limit(limit)
            ).all()
            return [
                ResourceImportJobView(
                    id=job.id,
                    file_name=job.file_name,
                    file_sha256=job.file_sha256,
                    status=job.status,
                    resource_id=job.resource_id,
                    duplicate_of_resource_id=job.duplicate_of_resource_id,
                    error_message=job.error_message,
                    retry_count=job.retry_count,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                )
                for job in jobs
            ]
