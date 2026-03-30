from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CorpusDataset(Base):
    __tablename__ = "corpus_datasets"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    data_kind: Mapped[str] = mapped_column(String(32), nullable=False)  # analysis | import
    domain: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="database", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    records: Mapped[list["CorpusRecord"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class CorpusRecord(Base):
    __tablename__ = "corpus_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("corpus_datasets.id"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    level: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    keywords_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    score_breakdown_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    rule_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    llm_explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    needs_attention: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    dataset: Mapped[CorpusDataset] = relationship(back_populates="records")
