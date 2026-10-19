export interface ResearchResourceSummary {
  id: string;
  title: string;
  resource_type: string;
  source_institution: string;
  source_url: string;
  publication_date: string | null;
  collected_at: string;
  file_format: string;
  copyright_status: string;
  fulltext_allowed: boolean;
  access_level: string;
  educator_name: string;
  author_names: string[];
  analysis_status: string;
  data_version: string;
  segment_count: number;
  updated_at: string;
}

export interface ResourceFile {
  id: string;
  original_name: string;
  media_type: string;
  extension: string;
  byte_size: number;
  sha256: string;
  parse_status: string;
  error_message: string;
  original_retained: boolean;
}

export interface ResourceSegment {
  id: string;
  ordinal: number;
  locator_type: string;
  locator_value: string;
  text: string;
  text_sha256: string;
}

export interface ResearchResourceDetail extends ResearchResourceSummary {
  original_locator: string;
  extracted_text: string;
  citation_text: string;
  content_sha256: string;
  authors: Array<{ name: string; role: string; organization: string }>;
  files: ResourceFile[];
  segments: ResourceSegment[];
}

export interface ResearchResourceListResponse {
  items: ResearchResourceSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ResearchResourceStats {
  total: number;
  fulltext_total: number;
  restricted_total: number;
  type_counts: Record<string, number>;
  analysis_status_counts: Record<string, number>;
  copyright_status_counts: Record<string, number>;
}

export interface ResourceImportResult {
  job_id: string;
  file_name: string;
  status: "succeeded" | "duplicate" | "failed";
  resource_id: string | null;
  duplicate_of_resource_id: string;
  segment_count: number;
  error_message: string;
}

export interface ResourceBatchImportResponse {
  total: number;
  succeeded: number;
  duplicates: number;
  failed: number;
  results: ResourceImportResult[];
}
