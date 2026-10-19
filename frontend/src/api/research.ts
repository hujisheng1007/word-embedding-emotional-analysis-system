import { request, requestForm } from "./client";
import type {
  ResearchResourceDetail,
  ResearchResourceListResponse,
  ResearchResourceStats,
  ResourceBatchImportResponse
} from "../types/research";

export interface ResourceFilters {
  keyword?: string;
  resourceType?: string;
  educatorName?: string;
  analysisStatus?: string;
  limit?: number;
  offset?: number;
}

export function getResourceStats(): Promise<ResearchResourceStats> {
  return request<ResearchResourceStats>("/research-resources/stats");
}

export function listResearchResources(filters: ResourceFilters): Promise<ResearchResourceListResponse> {
  const parameters = new URLSearchParams();
  if (filters.keyword) parameters.set("keyword", filters.keyword);
  if (filters.resourceType) parameters.set("resource_type", filters.resourceType);
  if (filters.educatorName) parameters.set("educator_name", filters.educatorName);
  if (filters.analysisStatus) parameters.set("analysis_status", filters.analysisStatus);
  parameters.set("limit", String(filters.limit ?? 50));
  parameters.set("offset", String(filters.offset ?? 0));
  return request<ResearchResourceListResponse>(`/research-resources?${parameters.toString()}`);
}

export function getResearchResource(resourceId: string): Promise<ResearchResourceDetail> {
  return request<ResearchResourceDetail>(`/research-resources/${encodeURIComponent(resourceId)}`);
}

export function importResearchResources(form: FormData): Promise<ResourceBatchImportResponse> {
  return requestForm<ResourceBatchImportResponse>("/research-resources/import", form);
}
