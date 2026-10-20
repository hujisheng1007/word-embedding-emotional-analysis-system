import { request } from "./client";
import type { EvaluationCase, EvaluationResponse, KnowledgeSearchResponse } from "../types/knowledge";

export function searchKnowledge(payload: { query: string; educator_name: string; resource_type: string; top_k: number }) {
  return request<KnowledgeSearchResponse>("/knowledge/search", {
    method: "POST", body: JSON.stringify(payload)
  });
}

export function evaluateRetrieval(payload: { name: string; cases: EvaluationCase[]; top_k: number }) {
  return request<EvaluationResponse>("/knowledge/evaluations", {
    method: "POST", body: JSON.stringify(payload)
  });
}
