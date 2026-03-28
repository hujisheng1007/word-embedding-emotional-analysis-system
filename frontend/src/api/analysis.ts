import { request } from "./client";
import type {
  AnalysisResult,
  BatchAnalysisRequest,
  BatchAnalysisResponse,
  SingleAnalysisRequest
} from "../types/analysis";

export function analyzeText(payload: SingleAnalysisRequest): Promise<AnalysisResult> {
  return request<AnalysisResult>("/analyze", {
    method: "POST",
    body: JSON.stringify({
      mode: "hybrid",
      ...payload
    })
  });
}

export function analyzeBatch(payload: BatchAnalysisRequest): Promise<BatchAnalysisResponse> {
  return request<BatchAnalysisResponse>("/analyze/batch", {
    method: "POST",
    body: JSON.stringify({
      mode: "hybrid",
      ...payload
    })
  });
}
