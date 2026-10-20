from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class CollectionSourceView(BaseModel):
    id: str
    name: str
    adapter_key: str
    source_type: str
    base_url: str
    terms_url: str
    robots_url: str
    license_note: str
    enabled: bool
    allows_metadata: bool
    allows_subtitles: bool
    allows_media_download: bool
    allows_transcription: bool
    rate_limit_per_minute: int
    schedule_interval_minutes: int
    last_run_at: datetime | None
    next_run_at: datetime | None


class CollectionJobCreate(BaseModel):
    source_id: str
    query: str = Field(min_length=1, max_length=300)
    educator_name: str = Field(default="", max_length=255)
    limit: int = Field(default=10, ge=1, le=25)
    language: str = Field(default="zh", max_length=16)
    contact_email: str = Field(default="", max_length=255)


class SourceScheduleUpdate(BaseModel):
    interval_minutes: int = Field(default=0, ge=0, le=10080)


class CollectionJobView(BaseModel):
    id: str
    source_id: str
    source_name: str
    job_type: str
    query: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    duplicate_count: int
    retry_count: int
    error_message: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CollectionLogView(BaseModel):
    id: str
    level: str
    event: str
    message: str
    context: dict
    created_at: datetime


class CollectionStats(BaseModel):
    source_count: int
    job_count: int
    running_count: int
    success_count: int
    failed_count: int
    duplicate_count: int
    person_count: int
    video_count: int
    transcript_count: int
    paper_count: int


class PersonFactView(BaseModel):
    id: str
    fact_type: str
    value_text: str
    source_url: str
    source_title: str
    source_publisher: str
    review_status: str


class EducatorPersonView(BaseModel):
    id: str
    display_name: str
    aliases: list[str]
    birth_date: str | None
    death_date: str | None
    identities: list[dict]
    facts: list[PersonFactView]
    resource_count: int


class ReviewUpdate(BaseModel):
    review_status: str = Field(pattern="^(pending|approved|rejected|corrected)$")
    corrected_text: str = ""


class TranscriptCueView(BaseModel):
    id: str
    sequence: int
    start_ms: int
    end_ms: int
    text: str
    review_status: str


class TranscriptView(BaseModel):
    id: str
    resource_id: str
    language: str
    origin: str
    model_name: str
    model_version: str
    review_status: str
    cues: list[TranscriptCueView]


class VideoView(BaseModel):
    id: str
    resource_id: str
    title: str
    educator_name: str
    page_url: str
    embed_url: str
    media_url: str
    license_code: str
    license_url: str
    embed_allowed: bool
    subtitle_access: bool
    download_allowed: bool
    transcription_allowed: bool
    restriction_reason: str
    transcripts: list[TranscriptView]


class SubtitleImportRequest(BaseModel):
    language: str = Field(default="zh", min_length=2, max_length=16)
    origin: str = Field(default="official_subtitle", pattern="^(official_subtitle|authorized_asr|imported)$")
    content: str = ""
    fetch_from_source: bool = False
    model_name: str = ""
    model_version: str = ""


class TranscriptionJobCreate(BaseModel):
    language: str = Field(default="zh", min_length=2, max_length=16)
    model_name: str = Field(default="base", min_length=1, max_length=128)


class ManualResourceCreate(BaseModel):
    source_id: str
    title: str = Field(min_length=1, max_length=500)
    source_url: HttpUrl
    resource_type: str = Field(pattern="^(video|webpage)$")
    educator_name: str = ""
    description: str = ""
    restriction_reason: str = "仅登记公开页面元数据；未获得媒体下载或转写授权"


class AnalysisEvidenceView(BaseModel):
    id: str
    dimension_id: str
    dimension_name: str
    score: float
    quote: str
    locator_type: str
    locator_value: str
    review_status: str


class ResourceAnalysisView(BaseModel):
    run_id: str
    resource_id: str
    status: str
    engine_version: str
    result: dict
    evidence: list[AnalysisEvidenceView]
