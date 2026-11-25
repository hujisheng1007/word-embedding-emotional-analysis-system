from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def large_text() -> Text:
    return Text().with_variant(LONGTEXT(), "mysql", "mariadb")


class PracticeCase(Base):
    __tablename__ = "practice_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="RESTRICT"), index=True
    )
    creation_key: Mapped[str] = mapped_column(String(64), unique=True)
    source_json: Mapped[str] = mapped_column(large_text())
    draft_revision: Mapped[int] = mapped_column(Integer, default=1)
    published_revision: Mapped[int | None] = mapped_column(Integer)
    withdrawn_through: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PracticeRevision(Base):
    __tablename__ = "practice_case_revisions"
    __table_args__ = (UniqueConstraint("case_id", "revision", name="uq_practice_case_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("practice_cases.id", ondelete="CASCADE"))
    revision: Mapped[int] = mapped_column(Integer)
    content_json: Mapped[str] = mapped_column(large_text())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewer: Mapped[str] = mapped_column(String(100), default="")
    review_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PracticeEvidence(Base):
    __tablename__ = "practice_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("practice_case_revisions.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(24))
    segment_id: Mapped[str] = mapped_column(String(36))
    start_char: Mapped[int] = mapped_column(Integer)
    end_char: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text)


class PracticeExtractionRun(Base):
    __tablename__ = "practice_extraction_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        ForeignKey("research_resources.id", ondelete="RESTRICT"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    input_json: Mapped[str] = mapped_column(large_text())
    config_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(large_text(), default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PracticeConcept(Base):
    __tablename__ = "practice_concepts"
    __table_args__ = (UniqueConstraint("kind", "normalized_label", name="uq_practice_concept_label"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    label: Mapped[str] = mapped_column(String(100))
    normalized_label: Mapped[str] = mapped_column(String(256))
    aliases_json: Mapped[str] = mapped_column(Text)


class PracticeCaseConcept(Base):
    __tablename__ = "practice_case_concepts"

    revision_id: Mapped[str] = mapped_column(
        ForeignKey("practice_case_revisions.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("practice_concepts.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
