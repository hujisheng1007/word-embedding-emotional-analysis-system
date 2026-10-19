from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class ResourceAuthorView(BaseModel):
    name: str
    role: str
    organization: str = ""


class ResourceFileView(BaseModel):
    id: str
    original_name: str
    media_type: str
    extension: str
    byte_size: int
    sha256: str
    parse_status: str
    error_message: str = ""
    original_retained: bool


class ResourceSegmentView(BaseModel):
    id: str
    ordinal: int
    locator_type: str
    locator_value: str
    text: str
    text_sha256: str


class ResearchResourceSummary(BaseModel):
    id: str
    title: str
    resource_type: str
    source_institution: str
    source_url: str
    publication_date: date | None
    collected_at: datetime
    file_format: str
    copyright_status: str
    fulltext_allowed: bool
    access_level: str
    educator_name: str = ""
    author_names: list[str] = Field(default_factory=list)
    analysis_status: str
    data_version: str
    segment_count: int = 0
    updated_at: datetime


class ResearchResourceDetail(ResearchResourceSummary):
    original_locator: str
    extracted_text: str
    citation_text: str
    content_sha256: str
    authors: list[ResourceAuthorView] = Field(default_factory=list)
    files: list[ResourceFileView] = Field(default_factory=list)
    segments: list[ResourceSegmentView] = Field(default_factory=list)


class ResearchResourceListResponse(BaseModel):
    items: list[ResearchResourceSummary]
    total: int
    limit: int
    offset: int


class ResearchResourceStats(BaseModel):
    total: int
    fulltext_total: int
    restricted_total: int
    type_counts: dict[str, int]
    analysis_status_counts: dict[str, int]
    copyright_status_counts: dict[str, int]


class ResourceImportResult(BaseModel):
    job_id: str
    file_name: str
    status: str
    resource_id: str | None = None
    duplicate_of_resource_id: str = ""
    segment_count: int = 0
    error_message: str = ""


class ResourceBatchImportResponse(BaseModel):
    total: int
    succeeded: int
    duplicates: int
    failed: int
    results: list[ResourceImportResult]


class ResourceImportJobView(BaseModel):
    id: str
    file_name: str
    file_sha256: str
    status: str
    resource_id: str | None
    duplicate_of_resource_id: str
    error_message: str
    retry_count: int
    started_at: datetime
    completed_at: datetime | None
