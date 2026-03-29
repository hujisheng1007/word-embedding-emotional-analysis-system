export interface ScoreFactor {
  name: string;
  value: number;
  description: string;
}

export interface AnalysisResult {
  text: string;
  category: string;
  level: string;
  score: number;
  keywords: string[];
  rule_reason: string;
  llm_explanation: string;
  needs_attention: boolean;
  score_breakdown?: ScoreFactor[];
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
  record_count: number;
  attention_count: number;
  updated_at: string;
  is_default: boolean;
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
