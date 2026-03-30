import { request } from "./client";
import type {
  AnalysisResult,
  BatchAnalysisRequest,
  BatchAnalysisResponse,
  DatasetOption,
  ExplanationRequest,
  ExplanationResponse,
  FoundationModelProfile,
  PublicSource,
  PublicSourceFetchRequest,
  PublicSourceFetchResponse,
  ReferenceLibraryResponse,
  SingleAnalysisRequest,
  SystemStatusResponse
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

export function generateExplanation(
  payload: ExplanationRequest
): Promise<ExplanationResponse> {
  return request<ExplanationResponse>("/explanations/generate", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getDefaultDataset(): Promise<BatchAnalysisResponse> {
  return request<BatchAnalysisResponse>("/datasets/default");
}

export function listDatasets(): Promise<DatasetOption[]> {
  return request<DatasetOption[]>("/datasets");
}

export function getDataset(datasetId: string): Promise<BatchAnalysisResponse> {
  return request<BatchAnalysisResponse>(`/datasets/${datasetId}`);
}

export function getReferenceLibrary(): Promise<ReferenceLibraryResponse> {
  return request<ReferenceLibraryResponse>("/reference-library");
}

export function listFoundationModelProfiles(): Promise<FoundationModelProfile[]> {
  return request<FoundationModelProfile[]>("/foundation-model/profiles");
}

export function activateFoundationModelProfile(profileId: string): Promise<SystemStatusResponse> {
  return request<SystemStatusResponse>("/foundation-model/activate", {
    method: "POST",
    body: JSON.stringify({ profile_id: profileId })
  });
}

export function listPublicSources(): Promise<PublicSource[]> {
  return request<PublicSource[]>("/public-sources");
}

export function fetchPublicSource(
  payload: PublicSourceFetchRequest
): Promise<PublicSourceFetchResponse> {
  return request<PublicSourceFetchResponse>("/public-sources/fetch", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getSystemStatus(): Promise<SystemStatusResponse> {
  return request<SystemStatusResponse>("/system/status");
}
