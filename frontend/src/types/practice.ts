export const fieldLabels = {
  context: "教育情境",
  problem: "实际问题",
  judgment: "判断依据",
  strategy: "行动策略",
  outcome: "原文所载结果"
} as const;

export type FieldName = keyof typeof fieldLabels;
export const fieldNames = Object.keys(fieldLabels) as FieldName[];
export type FieldState = "supported" | "not_stated" | "insufficient";
export const stateLabels: Record<FieldState, string> = {
  supported: "有原文支持",
  not_stated: "原文未载",
  insufficient: "证据不足"
};

export function formatLocator(type: string, value: string): string {
  const labels: Record<string, string> = {
    paragraph: "段落", page: "页码", timestamp: "时间戳", row: "行", json_path: "JSON 路径"
  };
  return value ? [labels[type], value].filter(Boolean).join(" ") : "原文片段";
}

export type ConceptKind = "context" | "problem" | "strategy";

export interface SourceSpan {
  segment_id: string;
  ordinal: number;
  text: string;
  locator_type: string;
  locator_value: string;
  text_sha256: string;
}

export interface Citation {
  segment_id: string;
  quote: string;
  start_char: number | null;
  end_char: number | null;
}

export interface Evidence extends Citation {
  id: string;
  locator_type: string;
  locator_value: string;
  text_sha256: string;
}

export interface PracticeField<T extends Citation = Citation> {
  state: FieldState;
  summary: string;
  evidence: T[];
}

export interface CaseContent {
  title: string;
  actor_name: string;
  fields: Record<FieldName, PracticeField>;
  interpretation: string;
  applicability: string;
  concept_ids: string[];
}

export interface SourceInfo {
  resource_id: string;
  title: string;
  source_institution: string;
  source_url: string;
  citation_text: string;
  data_version: string;
}

export interface Concept {
  id: string;
  kind: ConceptKind;
  label: string;
  aliases: string[];
}

export interface RevisionMeta {
  id: string;
  revision: number;
  reviewer: string;
  review_note: string;
  created_at: string;
  submitted_at: string | null;
  published_at: string | null;
}

export interface PublishedCase extends Omit<CaseContent, "concept_ids" | "fields"> {
  id: string;
  case_id: string;
  revision: number;
  source: SourceInfo;
  concepts: Concept[];
  fields: Record<FieldName, PracticeField<Evidence>>;
}

export interface PracticeCase extends PublishedCase, RevisionMeta {
  source: SourceInfo & { spans: SourceSpan[] };
  version: number;
  draft_revision: number;
  published_revision: number | null;
  withdrawn_through: number;
  history: RevisionMeta[];
}

export interface CaseEntry {
  id: string;
  title: string;
  resource_id: string;
  draft_revision: number;
  published_revision: number | null;
  submitted: boolean;
}

export interface ExtractionRun {
  id: string;
  resource_id: string;
  status: "queued" | "running" | "failed" | "succeeded";
  attempt: number;
  config: { model: string; profile_id: string; prompt_version: string };
  error: string;
  created_at: string;
  finished_at: string | null;
  can_retry: boolean;
  candidates: { segment_ids: string[]; content: CaseContent }[];
}

export interface CaseCard {
  id: string;
  title: string;
  revision: number;
  actor_name: string;
  problem: string;
  strategy: string;
  applicability: string;
  score?: number;
  matched_concepts?: string[];
}

export interface GraphNode {
  id: string;
  kind: "case" | "actor" | "context" | "problem" | "strategy" | "evidence";
  label: string;
  case_id?: string;
  revision?: number;
  evidence_id?: string;
}

export interface CaseGraphData {
  center: string;
  nodes: GraphNode[];
  edges: { source: string; target: string; relation: string }[];
}

export type LocatedEvidence = Evidence & { field: FieldName; source: SourceInfo };

export interface AnswerEvidence extends Evidence {
  case_id: string;
  revision: number;
  case_title: string;
  source_title: string;
  field: FieldName;
}

export interface TrainingAnswer {
  mode: "grounded" | "evidence" | "insufficient";
  message: string;
  claims: { text: string; evidence: AnswerEvidence[] }[];
  reflection_questions: string[];
}

export function blankContent(title = ""): CaseContent {
  const field = (): PracticeField => ({ state: "not_stated", summary: "", evidence: [] });
  return {
    title, actor_name: "", applicability: "", interpretation: "", concept_ids: [],
    fields: { context: field(), problem: field(), judgment: field(), strategy: field(), outcome: field() }
  };
}

export function contentFromCase(document: PracticeCase): CaseContent {
  const content = blankContent(document.title);
  content.actor_name = document.actor_name;
  content.applicability = document.applicability;
  content.interpretation = document.interpretation;
  content.concept_ids = document.concepts.map(item => item.id);
  for (const name of fieldNames) {
    const field = document.fields[name];
    content.fields[name] = {
      state: field.state,
      summary: field.summary,
      evidence: field.evidence.map(({ segment_id, quote, start_char, end_char }) => ({
        segment_id, quote, start_char, end_char
      }))
    };
  }
  return content;
}
