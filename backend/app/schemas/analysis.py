from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="待分析文本")
    mode: str = Field(default="hybrid", description="分析模式")


class AnalysisResult(BaseModel):
    text: str
    category: str
    level: str
    score: float
    keywords: list[str]
    rule_reason: str
    llm_explanation: str
    needs_attention: bool


class BatchAnalysisRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="批量待分析文本列表")
    mode: str = Field(default="hybrid", description="分析模式")


class KeywordCount(BaseModel):
    keyword: str
    count: int


class BatchAnalysisSummary(BaseModel):
    total: int
    category_distribution: dict[str, int]
    level_distribution: dict[str, int]
    top_keywords: list[KeywordCount]
    attention_count: int
    high_risk_texts: list[AnalysisResult]


class BatchAnalysisResponse(BaseModel):
    summary: BatchAnalysisSummary
    results: list[AnalysisResult]
