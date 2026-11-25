from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class MoralEvent(Base):
    __tablename__ = 'moral_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey('research_resources.id', ondelete='RESTRICT'), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    eligibility: Mapped[str] = mapped_column(String(24), default='candidate')
    review_revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MoralRun(Base):
    __tablename__ = 'moral_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('moral_events.id', ondelete='RESTRICT'), index=True)
    method: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    config_json: Mapped[str] = mapped_column(Text, default='{}')
    result_json: Mapped[str] = mapped_column(Text, default='{}')
    raw_output: Mapped[str] = mapped_column(Text, default='')
    error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MoralReview(Base):
    __tablename__ = 'moral_reviews'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('moral_events.id', ondelete='RESTRICT'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    reviewer: Mapped[str] = mapped_column(String(100))
    eligibility: Mapped[str] = mapped_column(String(24))
    codes_json: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
