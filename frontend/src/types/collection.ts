export interface CollectionSource {
  id: string; name: string; adapter_key: string; source_type: string; base_url: string;
  terms_url: string; robots_url: string; license_note: string; enabled: boolean;
  allows_metadata: boolean; allows_subtitles: boolean; allows_media_download: boolean;
  allows_transcription: boolean; rate_limit_per_minute: number;
  schedule_interval_minutes: number; last_run_at: string | null; next_run_at: string | null;
}

export interface CollectionStats {
  source_count: number; job_count: number; running_count: number; success_count: number;
  failed_count: number; duplicate_count: number; person_count: number; video_count: number;
  transcript_count: number; paper_count: number;
}

export interface CollectionJob {
  id: string; source_id: string; source_name: string; job_type: string; query: string;
  status: string; total_count: number; success_count: number; failed_count: number;
  duplicate_count: number; retry_count: number; error_message: string;
  created_at: string; started_at: string | null; completed_at: string | null;
}

export interface CollectionLog {
  id: string; level: string; event: string; message: string;
  context: Record<string, unknown>; created_at: string;
}

export interface PersonFact {
  id: string; fact_type: string; value_text: string; source_url: string;
  source_title: string; source_publisher: string; review_status: string;
}

export interface EducatorPerson {
  id: string; display_name: string; aliases: string[]; birth_date: string | null;
  death_date: string | null; identities: Array<Record<string, string | number>>;
  facts: PersonFact[]; resource_count: number;
}

export interface TranscriptCue {
  id: string; sequence: number; start_ms: number; end_ms: number; text: string; review_status: string;
}

export interface Transcript {
  id: string; resource_id: string; language: string; origin: string; model_name: string;
  model_version: string; review_status: string; cues: TranscriptCue[];
}

export interface CollectedVideo {
  id: string; resource_id: string; title: string; educator_name: string; page_url: string;
  embed_url: string; media_url: string; license_code: string; license_url: string;
  embed_allowed: boolean; subtitle_access: boolean; download_allowed: boolean;
  transcription_allowed: boolean; restriction_reason: string; transcripts: Transcript[];
}
