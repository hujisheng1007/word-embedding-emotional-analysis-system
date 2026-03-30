export interface ScoreFactor {
  name: string;
  value: number;
  description: string;
}

export interface MetricBenchmark {
  id: string;
  name: string;
  unit: string;
  description: string;
  low: number;
  medium: number;
  high: number;
}

export interface IndicatorMetricResult {
  id: string;
  name: string;
  unit: string;
  value: number;
  description: string;
  low: number;
  medium: number;
  high: number;
  band: string;
}

export interface DimensionScore {
  id: string;
  name: string;
  score: number;
  evidence_count: number;
  matched_keywords: string[];
  description: string;
}

export interface IndicatorScore {
  id: string;
  name: string;
  group_id: string;
  group_name: string;
  aspect_type: string;
  score: number;
  evidence_count: number;
  matched_keywords: string[];
  description: string;
  metric_results: IndicatorMetricResult[];
}

export interface TextSegmentPreview {
  index: number;
  excerpt: string;
  category: string;
  level: string;
  score: number;
  keywords: string[];
}

export interface AnalysisResult {
  text: string;
  text_length: number;
  category: string;
  level: string;
  score: number;
  keywords: string[];
  rule_reason: string;
  llm_explanation: string;
  needs_attention: boolean;
  score_breakdown?: ScoreFactor[];
  dominant_dimension_id?: string;
  dimension_scores?: DimensionScore[];
  indicator_scores?: IndicatorScore[];
  reference_quotes?: string[];
  is_long_text?: boolean;
  segment_count?: number;
  segment_previews?: TextSegmentPreview[];
}

export interface ExplanationRequest {
  text: string;
  category: string;
  level: string;
  keywords: string[];
  rule_reason: string;
  fallback?: string;
}

export interface ExplanationResponse {
  explanation: string;
}

export interface KeywordCount {
  keyword: string;
  count: number;
}

export interface BatchAnalysisSummary {
  total: number;
  category_distribution: Record<string, number>;
  level_distribution: Record<string, number>;
  top_keywords: KeywordCount[];
  wordcloud_keywords: KeywordCount[];
  attention_count: number;
  high_risk_texts: AnalysisResult[];
  avg_score: number;
}

export interface BatchAnalysisResponse {
  summary: BatchAnalysisSummary;
  results: AnalysisResult[];
}

export interface DatasetOption {
  id: string;
  name: string;
  description: string;
  file_name: string;
  data_kind: "analysis" | "import" | string;
  domain?: string;
  source?: string;
  record_count: number;
  attention_count: number;
  updated_at: string;
  is_default: boolean;
}

export interface ReferenceQuote {
  respondent_name: string;
  question_id: string;
  question: string;
  text: string;
}

export interface ReferenceIndicator {
  id: string;
  name: string;
  aspect_type: string;
  description: string;
  question_ids: string[];
  keyword_cues: string[];
  metric_benchmarks: MetricBenchmark[];
}

export interface ReferenceDimension {
  id: string;
  name: string;
  description: string;
  question_ids: string[];
  keyword_cues: string[];
  excerpt_count: number;
  indicators: ReferenceIndicator[];
  highlight_terms: KeywordCount[];
  sample_quotes: ReferenceQuote[];
}

export interface ReferenceLibraryResponse {
  source_name: string;
  source_file: string;
  total_excerpts: number;
  total_respondents: number;
  dimensions: ReferenceDimension[];
}

export interface ImportSummary {
  total_entries: number;
  extracted_count: number;
  duplicates_removed: number;
  empty_removed: number;
  detected_column: string | null;
  file_type: "txt" | "csv";
}

export interface SingleAnalysisRequest {
  text: string;
  mode?: string;
}

export interface BatchAnalysisRequest {
  texts: string[];
  mode?: string;
}

export interface PublicSource {
  id: string;
  name: string;
  description: string;
  feed_url: string;
}

export interface PublicSourceFetchRequest {
  source_id: string;
  limit?: number;
}

export interface PublicSourceFetchResponse {
  source: PublicSource;
  fetched_count: number;
  texts: string[];
  analysis: BatchAnalysisResponse;
}

export interface FoundationModelProfile {
  id: string;
  label: string;
  provider: string;
  base_url: string;
  model_name: string;
  description: string;
  requires_api_key: boolean;
  configured: boolean;
  active: boolean;
}

export interface SystemStatusResponse {
  llm_enabled: boolean;
  llm_model: string;
  llm_base_url: string;
  local_llm_model_path: string;
  foundation_model_enabled: boolean;
  foundation_model_name: string;
  active_foundation_profile_id: string;
  foundation_model_ready: boolean;
}
