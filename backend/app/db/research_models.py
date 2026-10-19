from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
