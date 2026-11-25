export type ComponentId = 'sensitivity' | 'judgment' | 'motivation' | 'implementation';
export type EvidenceStatus = 'supported' | 'not_mentioned' | 'insufficient' | 'counterevidence' | 'mixed';
export type MoralMethod = 'rule' | 'llm_direct' | 'llm_evidence';
export interface MoralEvidence { segment_id: string; quote: string; polarity: 'support'|'counter'|'context'; start_char?:number|null; end_char?:number|null }
export interface MoralCode { component_id:ComponentId; status:EvidenceStatus; rationale:string; evidence:MoralEvidence[] }
export interface MoralResource { id:string; title:string; educator_name:string; resource_type:string; segment_count:number; analyzable:boolean; source_institution:string }
export interface SourceSpan { segment_id:string; ordinal:number; text:string; locator_type:string; locator_value:string }
export interface EventSummary { id:string; resource_id:string; resource_title:string; educator_name:string; resource_type:string; eligibility:string; review_revision:number; excerpt:string; created_at:string }
export interface MoralRun {id:string;method:MoralMethod;status:string;error:string;config:Record<string,unknown>; result:{codes?:MoralCode[];citation_check?:string};created_at:string}
export interface MoralReview {id:string;revision:number;reviewer:string;eligibility:'confirmed'|'excluded';codes:MoralCode[];note:string;created_at:string}
export interface MoralEvent extends EventSummary {snapshot:{resource_title:string;educator_name:string;source_url:string;source_institution:string;analysis_modality:string;selection_method:string;spans:SourceSpan[]};input_hash:string;runs:MoralRun[];reviews:MoralReview[]}
export interface MoralStats {events:number;confirmed:number;candidate:number;excluded:number;failed_runs:number;people:{name:string;events:number;confirmed:number}[];component_counts:Record<ComponentId,Record<EvidenceStatus,number>>;denominator:number;note:string}
