from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class EducatorPerson(Base):
    __tablename__ = "educator_persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    death_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    resources: Mapped[list["ResearchResource"]] = relationship(back_populates="educator")


class ResearchResource(Base):
    __tablename__ = "research_resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_institution: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    file_format: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    copyright_status: Mapped[str] = mapped_column(String(64), index=True, default="unknown", nullable=False)
    fulltext_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_level: Mapped[str] = mapped_column(String(32), index=True, default="restricted", nullable=False)
    original_locator: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    educator_person_id: Mapped[str | None] = mapped_column(
        ForeignKey("educator_persons.id", ondelete="SET NULL"), index=True, nullable=True
    )
    analysis_status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), default="1", nullable=False)
    citation_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    educator: Mapped[EducatorPerson | None] = relationship(back_populates="resources")
    authors: Mapped[list["ResourceAuthor"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
    files: Mapped[list["ResourceFile"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
    segments: Mapped[list["ResourceSegment"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
    import_jobs: Mapped[list["ResourceImportJob"]] = relationship(back_populates="resource")


class ResourceAuthor(Base):
    __tablename__ = "resource_authors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(64), default="author", nullable=False)
    organization: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    resource: Mapped[ResearchResource] = relationship(back_populates="authors")


class ResourceFile(Base):
    __tablename__ = "resource_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    media_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    extension: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    resource: Mapped[ResearchResource] = relationship(back_populates="files")
    segments: Mapped[list["ResourceSegment"]] = relationship(back_populates="resource_file")


class ResourceSegment(Base):
    __tablename__ = "resource_segments"
    __table_args__ = (UniqueConstraint("resource_id", "ordinal", name="uq_resource_segment_ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resource_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("resource_files.id", ondelete="SET NULL"), index=True, nullable=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    locator_type: Mapped[str] = mapped_column(String(32), default="paragraph", nullable=False)
    locator_value: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    resource: Mapped[ResearchResource] = relationship(back_populates="segments")
    resource_file: Mapped[ResourceFile | None] = relationship(back_populates="segments")


class ResourceImportJob(Base):
    __tablename__ = "resource_import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), index=True, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_resources.id", ondelete="SET NULL"), index=True, nullable=True
    )
    duplicate_of_resource_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    resource: Mapped[ResearchResource | None] = relationship(back_populates="import_jobs")


class CollectionSource(Base):
    __tablename__ = "collection_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    terms_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    robots_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    license_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allows_metadata: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allows_subtitles: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allows_media_download: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allows_transcription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("collection_sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    query_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="queued", nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    pause_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("collection_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    level: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    event: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ResourceIdentifier(Base):
    __tablename__ = "resource_identifiers"
    __table_args__ = (UniqueConstraint("scheme", "value", name="uq_resource_identifier"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheme: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)


class PersonExternalIdentity(Base):
    __tablename__ = "person_external_identities"
    __table_args__ = (UniqueConstraint("source_key", "external_id", name="uq_person_external_identity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(
        ForeignKey("educator_persons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PersonFact(Base):
    __tablename__ = "person_facts"
    __table_args__ = (UniqueConstraint("person_id", "content_sha256", name="uq_person_fact_content"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(
        ForeignKey("educator_persons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resource_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_resources.id", ondelete="SET NULL"), index=True, nullable=True
    )
    fact_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    value_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_publisher: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)
    extracted_by: Mapped[str] = mapped_column(String(64), default="adapter", nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class VideoAsset(Base):
    __tablename__ = "video_assets"
    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_video_asset_external"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    page_url: Mapped[str] = mapped_column(Text, nullable=False)
    embed_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    media_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    license_code: Mapped[str] = mapped_column(String(128), default="unknown", nullable=False)
    license_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    embed_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subtitle_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    download_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transcription_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    restriction_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("video_assets.id", ondelete="CASCADE"), index=True, nullable=True
    )
    language: Mapped[str] = mapped_column(String(32), default="und", nullable=False)
    origin: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)
    full_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class TranscriptCue(Base):
    __tablename__ = "transcript_cues"
    __table_args__ = (UniqueConstraint("transcript_id", "sequence", name="uq_transcript_cue_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transcript_id: Mapped[str] = mapped_column(
        ForeignKey("transcripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)


class PersonalityAnalysisRun(Base):
    __tablename__ = "personality_analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    transcript_id: Mapped[str | None] = mapped_column(
        ForeignKey("transcripts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PersonalityEvidence(Base):
    __tablename__ = "personality_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("personality_analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    transcript_cue_id: Mapped[str | None] = mapped_column(
        ForeignKey("transcript_cues.id", ondelete="SET NULL"), index=True, nullable=True
    )
    dimension_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    locator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    locator_value: Mapped[str] = mapped_column(String(255), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)
