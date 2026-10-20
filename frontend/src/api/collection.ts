import { request } from "./client";
import type {
  CollectedVideo, CollectionJob, CollectionLog, CollectionSource, CollectionStats, EducatorPerson
} from "../types/collection";

export const getCollectionSources = () => request<CollectionSource[]>("/collection/sources");
export const getCollectionStats = () => request<CollectionStats>("/collection/stats");
export const getCollectionJobs = () => request<CollectionJob[]>("/collection/jobs");
export const getJobLogs = (id: string) => request<CollectionLog[]>(`/collection/jobs/${id}/logs`);
export const getPeople = (keyword = "") => request<EducatorPerson[]>(`/collection/people?keyword=${encodeURIComponent(keyword)}`);
export const getVideos = (keyword = "") => request<CollectedVideo[]>(`/collection/videos?keyword=${encodeURIComponent(keyword)}`);

export function createCollectionJob(payload: {
  source_id: string; query: string; educator_name: string; limit: number; language: string; contact_email: string;
}) {
  return request<{ job_id: string; status: string }>("/collection/jobs", {
    method: "POST", body: JSON.stringify(payload)
  });
}

export const pauseCollectionJob = (id: string) => request(`/collection/jobs/${id}/pause`, { method: "POST" });
export const resumeCollectionJob = (id: string) => request(`/collection/jobs/${id}/resume`, { method: "POST" });

export function importOfficialSubtitle(videoId: string, language: string) {
  return request<{ transcript_id: string }>(`/collection/videos/${videoId}/subtitles`, {
    method: "POST",
    body: JSON.stringify({ language, origin: "official_subtitle", content: "", fetch_from_source: true })
  });
}

export function transcribeAuthorizedVideo(videoId: string) {
  return request<{ job_id: string }>(`/collection/videos/${videoId}/transcribe`, {
    method: "POST", body: JSON.stringify({ language: "zh", model_name: "base" })
  });
}

export function updateReview(path: string, reviewStatus: string, correctedText = "") {
  return request(path, {
    method: "PATCH", body: JSON.stringify({ review_status: reviewStatus, corrected_text: correctedText })
  });
}

export const analyzeCollectedResource = (resourceId: string) => request(
  `/collection/resources/${resourceId}/analyze`, { method: "POST" }
);
