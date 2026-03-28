export interface AnalysisResult {
  text: string;
  category: string;
  level: string;
  score: number;
  keywords: string[];
  rule_reason: string;
  llm_explanation: string;
  needs_attention: boolean;
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
  attention_count: number;
  high_risk_texts: AnalysisResult[];
}

export interface BatchAnalysisResponse {
  summary: BatchAnalysisSummary;
  results: AnalysisResult[];
}

export interface SingleAnalysisRequest {
  text: string;
  mode?: string;
}

export interface BatchAnalysisRequest {
  texts: string[];
  mode?: string;
}
