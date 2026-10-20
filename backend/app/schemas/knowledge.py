from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    educator_name: str = Field(default="", max_length=255)
    resource_type: str = Field(default="", max_length=64)
    top_k: int = Field(default=10, ge=1, le=50)


class KnowledgeHit(BaseModel):
    resource_id: str
    resource_title: str
    resource_type: str
    educator_name: str
    source_url: str
    copyright_status: str
    segment_id: str
    locator_type: str
    locator_value: str
    excerpt: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    run_id: str
    query: str
    total_candidates: int
    hits: list[KnowledgeHit]


class EvaluationCase(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    expected_resource_ids: list[str] = Field(min_length=1)
    educator_name: str = ""
    resource_type: str = ""


class RetrievalEvaluationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)
    top_k: int = Field(default=10, ge=1, le=50)


class EvaluationCaseResult(BaseModel):
    query: str
    expected_resource_ids: list[str]
    retrieved_resource_ids: list[str]
    first_relevant_rank: int | None
    hit: bool


class RetrievalEvaluationResponse(BaseModel):
    run_id: str
    name: str
    top_k: int
    case_count: int
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    results: list[EvaluationCaseResult]
    created_at: datetime
