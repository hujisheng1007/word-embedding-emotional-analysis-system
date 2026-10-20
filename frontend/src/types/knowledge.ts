export interface KnowledgeHit {
  resource_id: string; resource_title: string; resource_type: string; educator_name: string;
  source_url: string; copyright_status: string; segment_id: string; locator_type: string;
  locator_value: string; excerpt: string; score: number;
}

export interface KnowledgeSearchResponse {
  run_id: string; query: string; total_candidates: number; hits: KnowledgeHit[];
}

export interface EvaluationCase {
  query: string; expected_resource_ids: string[]; educator_name?: string; resource_type?: string;
}

export interface EvaluationResponse {
  run_id: string; name: string; top_k: number; case_count: number;
  hit_rate_at_k: number; mean_reciprocal_rank: number;
  results: Array<{ query: string; expected_resource_ids: string[]; retrieved_resource_ids: string[]; first_relevant_rank: number | null; hit: boolean }>;
  created_at: string;
}
