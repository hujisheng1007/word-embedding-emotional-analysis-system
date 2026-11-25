import { request } from "./client";
import type {
  CaseCard, CaseContent, CaseEntry, CaseGraphData, Concept, ConceptKind, ExtractionRun,
  LocatedEvidence, PracticeCase, PublishedCase, TrainingAnswer
} from "../types/practice";

const id = encodeURIComponent;
const json = (method: string, body: unknown = {}) => ({ method, body: JSON.stringify(body) });
const cases = "/practice/cases";
const runs = "/practice/extractions";
const training = "/training/cases";
const versionQuery = (revision?: number) => revision ? "?revision=" + revision : "";

export const caseEntries = (resourceId: string, offset = 0) =>
  request<CaseEntry[]>(cases + "?resource_id=" + id(resourceId) + "&offset=" + offset);
export const caseDetail = (caseId: string, revision?: number) =>
  request<PracticeCase>(cases + "/" + id(caseId) + versionQuery(revision));
export const createCase = (resource_id: string, segment_ids: string[], content: CaseContent, request_id?: string) =>
  request<PracticeCase>(cases, json("POST", { resource_id, segment_ids, content, request_id }));
export const saveCase = (caseId: string, expected_version: number, content: CaseContent) =>
  request<PracticeCase>(cases + "/" + id(caseId) + "/draft", json("PUT", { expected_version, content }));

export const submitCase = (caseId: string, expected_version: number) =>
  request<PracticeCase>(cases + "/" + id(caseId) + "/submit", json("POST", { expected_version }));
export const withdrawCase = (caseId: string, expected_version: number) =>
  request<PracticeCase>(cases + "/" + id(caseId) + "/withdraw", json("POST", { expected_version }));
export const publishCase = (
  caseId: string, expected_version: number, reviewer: string, note: string, training_allowed: boolean, confirmed: boolean
) => request<PracticeCase>(cases + "/" + id(caseId) + "/publish", json("POST", {
  expected_version, reviewer, note, training_allowed, confirmed
}));

export const concepts = () => request<Concept[]>("/practice/concepts");
export const createConcept = (kind: ConceptKind, label: string, aliases: string[]) =>
  request<Concept>("/practice/concepts", json("POST", { kind, label, aliases }));
export const extractions = (resourceId: string) =>
  request<ExtractionRun[]>(runs + "?resource_id=" + id(resourceId));
export const extract = (resource_id: string, segment_ids: string[]) =>
  request<ExtractionRun>(runs, json("POST", { resource_id, segment_ids }));
export const retryExtraction = (runId: string) =>
  request<ExtractionRun>(runs + "/" + id(runId) + "/retry", json("POST"));
export const acceptCandidate = (runId: string, index: number) =>
  request<PracticeCase>(runs + "/" + id(runId) + "/candidates/" + index + "/accept", json("POST"));

export const browseCases = (offset = 0) =>
  request<CaseCard[]>(training + "?offset=" + offset);
export const searchCases = (query: string, top_k = 8) =>
  request<CaseCard[]>(training + "/search", json("POST", { query, top_k }));
export const publishedCase = (caseId: string, revision?: number) =>
  request<PublishedCase>(training + "/" + id(caseId) + versionQuery(revision));
export const caseGraph = (caseId: string, revision?: number) =>
  request<CaseGraphData>(training + "/" + id(caseId) + "/graph" + versionQuery(revision));
export const locateEvidence = (caseId: string, revision: number, evidenceId: string) =>
  request<LocatedEvidence>(training + "/" + id(caseId) + "/evidence/" + id(evidenceId) + versionQuery(revision));
export const ask = (query: string) =>
  request<TrainingAnswer>("/training/answers", json("POST", { query }));
