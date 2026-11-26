from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

FieldName = Literal["context", "problem", "judgment", "strategy", "outcome"]
ConceptKind = Literal["context", "problem", "strategy"]
FIELD_LABELS: dict[FieldName, str] = {
    "context": "教育情境",
    "problem": "实际问题",
    "judgment": "判断依据",
    "strategy": "行动策略",
    "outcome": "原文所载结果",
}
REQUIRED_FIELDS = ("context", "problem", "strategy")
Identifier = Annotated[str, Field(min_length=1, max_length=36)]


class PracticeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Quote(PracticeInput):
    model_config = ConfigDict(str_strip_whitespace=False)
    segment_id: Identifier
    quote: str = Field(min_length=1, max_length=1500)
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def complete_range(self) -> "Quote":
        if (self.start_char is None) != (self.end_char is None):
            raise ValueError("引文起止位置须同时填写")
        return self


class PracticeField(PracticeInput):
    state: Literal["supported", "not_stated", "insufficient"] = "not_stated"
    summary: str = Field(default="", max_length=2000)
    evidence: list[Quote] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def supported_field_has_evidence(self) -> "PracticeField":
        if self.state == "supported" and (not self.summary or not self.evidence):
            raise ValueError("标为有原文支持的字段须填写说明并提供引文")
        return self


class PracticeFields(PracticeInput):
    context: PracticeField = Field(default_factory=PracticeField)
    problem: PracticeField = Field(default_factory=PracticeField)
    judgment: PracticeField = Field(default_factory=PracticeField)
    strategy: PracticeField = Field(default_factory=PracticeField)
    outcome: PracticeField = Field(default_factory=PracticeField)


class CaseContent(PracticeInput):
    title: str = Field(min_length=1, max_length=200)
    actor_name: str = Field(default="", max_length=150)
    fields: PracticeFields = Field(default_factory=PracticeFields)
    interpretation: str = Field(default="", max_length=2000)
    applicability: str = Field(default="", max_length=2000)
    concept_ids: list[Identifier] = Field(default_factory=list, max_length=30)


class SourceSelection(PracticeInput):
    resource_id: Identifier
    segment_ids: list[Identifier] = Field(min_length=1, max_length=30)


class CreateCase(SourceSelection):
    content: CaseContent
    request_id: UUID | None = None


class VersionedAction(PracticeInput):
    expected_version: int = Field(ge=1)


class SaveCase(VersionedAction):
    content: CaseContent


class PublishCase(VersionedAction):
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=2000)
    training_allowed: Literal[True]
    confirmed: Literal[True]


class NewConcept(PracticeInput):
    kind: ConceptKind
    label: str = Field(min_length=1, max_length=100)
    aliases: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=12
    )


class Candidate(PracticeInput):
    segment_ids: list[Identifier] = Field(min_length=1, max_length=30)
    content: CaseContent


class ExtractionOutput(PracticeInput):
    candidates: list[Candidate] = Field(max_length=8)


class CaseSearch(PracticeInput):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class CaseQueryExpansion(PracticeInput):
    concept_ids: list[Identifier] = Field(default_factory=list, max_length=4)
    search_phrases: list[Annotated[str, Field(min_length=2, max_length=60)]] = Field(
        default_factory=list, max_length=5
    )


class PublishedCaseLookup(PracticeInput):
    queries: list[Annotated[str, Field(min_length=2, max_length=100)]] = Field(min_length=1, max_length=4)
    limit: int = Field(default=4, ge=1, le=5)


class PublishedCaseCatalog(PracticeInput):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=12, ge=1, le=20)


class PublishedCaseReference(PracticeInput):
    case_id: Identifier
    revision: int = Field(ge=1)


class AnswerClaim(PracticeInput):
    text: str = Field(min_length=1, max_length=1200)
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=8)


class ModelAnswer(PracticeInput):
    answer: str = Field(min_length=1, max_length=900)
    evidence_fit: Literal["direct", "indirect", "none"]
    claims: list[AnswerClaim] = Field(max_length=8)
    next_step: str = Field(default="", max_length=400)
    clarifying_question: str = Field(default="", max_length=250)
    reflection_questions: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        default_factory=list, max_length=4
    )

    @model_validator(mode="after")
    def evidence_fit_matches_claims(self) -> "ModelAnswer":
        if (self.evidence_fit == "none") != (not self.claims):
            raise ValueError("证据适配程度须与引证内容一致")
        return self


class EvaluationCase(PracticeInput):
    query: str = Field(min_length=1, max_length=1000)
    expected_case_ids: list[Identifier] = Field(min_length=1, max_length=30)


class CaseEvaluation(PracticeInput):
    top_k: int = Field(default=5, ge=1, le=20)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=50)
