from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Component = Literal['sensitivity', 'judgment', 'motivation', 'implementation']
EvidenceStatus = Literal['supported', 'not_mentioned', 'insufficient', 'counterevidence', 'mixed']
Method = Literal['rule', 'llm_direct', 'llm_evidence']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Evidence(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    segment_id: str
    quote: str = Field(min_length=1, max_length=6000)
    polarity: Literal['support', 'counter', 'context'] = 'support'
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=1)

class ComponentCode(StrictModel):
    component_id: Component
    status: EvidenceStatus
    rationale: str = Field(min_length=1, max_length=3000)
    evidence: list[Evidence] = Field(default_factory=list, max_length=12)

class Coding(StrictModel):
    codes: list[ComponentCode] = Field(min_length=4, max_length=4)

    @model_validator(mode='after')
    def all_components(self):
        if {c.component_id for c in self.codes} != {'sensitivity','judgment','motivation','implementation'}:
            raise ValueError('必须分别包含四个成分，不能重复或遗漏')
        return self

class BuildEvents(StrictModel):
    resource_ids: list[str] = Field(min_length=1, max_length=30)
    per_resource: int = Field(default=3, ge=1, le=5)
    radius: int = Field(default=2, ge=0, le=4)
    keyword: str = Field(default='', max_length=500)
    before: int | None = Field(default=None, ge=0, le=10)
    after: int | None = Field(default=None, ge=0, le=10)
    min_keyword_hits: int = Field(default=1, ge=1, le=20)

class CreateEvent(StrictModel):
    resource_id: str
    segment_ids: list[str] = Field(min_length=1, max_length=30)

class AnalyzeEvent(StrictModel):
    method: Method = 'rule'

class ReviewEvent(Coding):
    expected_revision: int = Field(ge=0)
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(default='', max_length=4000)
    eligibility: Literal['confirmed', 'excluded'] = 'confirmed'
