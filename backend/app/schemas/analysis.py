from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="待分析文本")
    mode: str = Field(default="hybrid", description="分析模式")


class ScoreFactor(BaseModel):
    name: str
    value: float
    description: str


class MetricBenchmark(BaseModel):
    id: str
    name: str
    unit: str
    description: str
    low: float
    medium: float
    high: float


class IndicatorMetricResult(BaseModel):
    id: str
    name: str
    unit: str
    value: float
    description: str
    low: float
    medium: float
    high: float
    band: str


class DimensionScore(BaseModel):
    id: str
    name: str
    score: float
    evidence_count: int
    matched_keywords: list[str] = Field(default_factory=list)
    description: str = ""


class IndicatorScore(BaseModel):
    id: str
    name: str
    group_id: str
    group_name: str
    aspect_type: str
    score: float
    evidence_count: int
    matched_keywords: list[str] = Field(default_factory=list)
    description: str = ""
    metric_results: list[IndicatorMetricResult] = Field(default_factory=list)


class TextSegmentPreview(BaseModel):
    index: int
    excerpt: str
    category: str
    level: str
    score: float
    keywords: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    text: str
    text_length: int = 0
    category: str
    level: str
    score: float
    keywords: list[str]
    rule_reason: str
    llm_explanation: str
    needs_attention: bool
    score_breakdown: list[ScoreFactor] = Field(default_factory=list)
    dominant_dimension_id: str = ""
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    indicator_scores: list[IndicatorScore] = Field(default_factory=list)
    reference_quotes: list[str] = Field(default_factory=list)
    is_long_text: bool = False
    segment_count: int = 0
    segment_previews: list[TextSegmentPreview] = Field(default_factory=list)


class ExplanationRequest(BaseModel):
    text: str = Field(..., min_length=1, description="待生成解释的原始文本")
    category: str = Field(..., min_length=1, description="当前分析类别")
    level: str = Field(..., min_length=1, description="当前分析等级")
    keywords: list[str] = Field(default_factory=list, description="命中关键词")
    rule_reason: str = Field(..., min_length=1, description="规则判定依据")
    fallback: str = Field(default="", description="已有解释或兜底解释")


class ExplanationResponse(BaseModel):
    explanation: str


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
    wordcloud_keywords: list[KeywordCount]
    attention_count: int
    high_risk_texts: list[AnalysisResult]
    avg_score: float = 0.0


class BatchAnalysisResponse(BaseModel):
    summary: BatchAnalysisSummary
    results: list[AnalysisResult]


class DatasetOption(BaseModel):
    id: str
    name: str
    description: str
    file_name: str
    data_kind: str
    domain: str = "general"
    source: str = "database"
    record_count: int
    attention_count: int
    updated_at: str
    is_default: bool


class ReferenceQuote(BaseModel):
    respondent_name: str
    question_id: str
    question: str
    text: str


class ReferenceIndicator(BaseModel):
    id: str
    name: str
    aspect_type: str
    description: str
    question_ids: list[str]
    keyword_cues: list[str]
    metric_benchmarks: list[MetricBenchmark]


class ReferenceDimension(BaseModel):
    id: str
    name: str
    description: str
    question_ids: list[str]
    keyword_cues: list[str]
    excerpt_count: int
    indicators: list[ReferenceIndicator] = Field(default_factory=list)
    highlight_terms: list[KeywordCount]
    sample_quotes: list[ReferenceQuote]


class ReferenceLibraryResponse(BaseModel):
    source_name: str
    source_file: str
    total_excerpts: int
    total_respondents: int
    dimensions: list[ReferenceDimension]


class PublicSource(BaseModel):
    id: str
    name: str
    description: str
    feed_url: str


class PublicSourceFetchRequest(BaseModel):
    source_id: str = Field(..., description="公开数据源 ID")
    limit: int = Field(default=8, ge=1, le=20, description="抓取条数")


class PublicSourceFetchResponse(BaseModel):
    source: PublicSource
    fetched_count: int
    texts: list[str]
    analysis: BatchAnalysisResponse


class FoundationModelProfile(BaseModel):
    id: str
    label: str
    provider: str
    base_url: str
    model_name: str
    description: str
    requires_api_key: bool
    configured: bool
    active: bool


class ActivateFoundationModelProfileRequest(BaseModel):
    profile_id: str = Field(..., description="要激活的强模型档案 ID")


class SystemStatusResponse(BaseModel):
    llm_enabled: bool
    llm_model: str
    llm_base_url: str
    local_llm_model_path: str
    foundation_model_enabled: bool
    foundation_model_name: str
    active_foundation_profile_id: str
    foundation_model_ready: bool
