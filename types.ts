
export enum Language {
  EN = 'en',
  FR = 'fr',
  DE = 'de',
  IT = 'it',
  JA = 'ja'
}

export type SearchMode = 'rag' | 'semantic';

export interface KnowledgeChunk {
  id: string;
  content: string;
  source_id: string;
  source_title: string;
  source_url: string;
  language: Language;
  section_reference: string;
  effective_date_start: string;
  effective_date_end?: string | null; // Added for time travel
  doc_type: 'legislation' | 'policy' | 'guidance';
  themes?: string;
  category?: string; // Added for metadata
  score: number; // Added for semantic ranking
  summary?: string; // Added for on-demand summarization
}

export interface Citation {
  doc_id: string;
  locator: string;
  title?: string;
  snippet?: string;
  category?: string; // Added for UI badges
}

export interface RagResponse {
  type: 'rag';
  answer: string;
  lang: string;
  bullets: string[];
  citations: Citation[];
  confidence: number;
  abstained: boolean;
  categories?: string[]; // Aggregated from sources
  aggregated_themes?: string[]; // Aggregated from sources
}

export interface SemanticSearchResponse {
    type: 'semantic';
    results: KnowledgeChunk[];
}

export type SearchResult = RagResponse | SemanticSearchResponse;

export interface TraceStep {
  clause: string;
  reason: string;
  version: string;
  source_id?: string; // Added for traceability
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface DecisionResult {
  eligible: boolean;
  effective_date: string;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface RulesResponse {
  decision: DecisionResult;
  explanation?: string; // LLM-generated summary of decision reason
  trace: TraceStep[];
  sources: string[];
}

// --- Legislative Source Integration Types ---

export interface LegislativeExcerpt {
  text: string;                        // Verbatim legislative text
  citation: string;                    // Full citation (e.g., "IRPA s. 12(1)(a)")
  act_name: string;                    // Full act name
  section_title?: string;              // Section heading if available
  plain_language?: string;             // Plain language explanation
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface DecisionTreeNode {
  id: string;
  type: 'condition' | 'decision';
  label: string;                       // Short description for display
  condition_text?: string;             // e.g., "salary_offer >= 66000"
  legislative_excerpt?: LegislativeExcerpt;
  result?: 'pass' | 'fail' | 'unknown';
  children: DecisionTreeNode[];
}

export interface LegislationMap {
  primary: LegislativeExcerpt[];       // Directly applicable legislation
  related: LegislativeExcerpt[];       // Contextual/secondary legislation
  definitions: LegislativeExcerpt[];   // Relevant definitions from legislation
}

export interface EnhancedRulesResponse extends RulesResponse {
  decision_tree?: DecisionTreeNode;
  legislation_map?: LegislationMap;
}

// New interface for the streaming response from the LexGraph agent
export interface RulesResponseStream {
  query: string;
  language: string;
  effective_date: string;
  generated_queries: string[];
  documents: string[];
  citations_found: string[];
  trace_log: string[];
  loop_count: number;
  final_answer: string; // This will hold the JSON string of RulesResponse when synthesis is done
  eligible?: boolean;
  decision_trace?: TraceStep[]; // Parsed decision trace from final_answer
  extracted_rules?: string; // JSON string of extracted rules
  resolved_rules?: string; // JSON string of resolved rules with confidence
  // Legislative source integration fields
  legislative_excerpts?: LegislativeExcerpt[];
  decision_tree?: DecisionTreeNode;
  legislation_map?: LegislationMap;
}

// Step card progress types for LexGraph UI
export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export type LexGraphNodeName = 'retrieve' | 'extract_rules' | 'resolve_thresholds' | 'map_legislation' | 'extract_facts' | 'evaluate';

export interface StepData {
  retrieve: { status: StepStatus; documents: string[]; };
  extract_rules: { status: StepStatus; rules: ExtractedRule[]; };
  resolve_thresholds: { status: StepStatus; resolvedRules: ExtractedRule[]; confidenceCounts: { high: number; medium: number; low: number; }; };
  map_legislation: { status: StepStatus; legislationMap: LegislationMap | null; };
  extract_facts: { status: StepStatus; facts: Record<string, unknown>; };
  evaluate: { status: StepStatus; decision: DecisionResult | null; trace: TraceStep[]; decisionTree: DecisionTreeNode | null; };
}

export interface ExtractedRule {
  rule_id: string;
  description?: string;
  source_document?: string;
  source_section?: string;
  conditions?: RuleCondition[];
  outcome?: { eligible: boolean; program?: string; };
}

export interface RuleCondition {
  fact_key: string;
  operator: string;
  value: unknown;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface LexGraphStreamEvent {
  node: LexGraphNodeName;
  state: RulesResponseStream;
}

// Graph visualization types
export interface GraphNode {
  id: string;
  label: string;
  group: number; // 1 = rule (blue), 2 = condition (red)
}

export interface GraphLink {
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// New interface for the streaming response from the GovLens agent
export interface GovLensResponseStream {
  query: string;
  language: string;
  search_strategy: string;
  generated_queries: string[];
  documents: string[];
  trace_log: string[];
  loop_count: number;
  final_answer: string; // Raw JSON response
}

export interface AllocationData {
  region: string;
  demand: number;
  allocated: number;
  capacity: number;
  optimized: number;
}

export interface AccessField {
  key: string;
  value: string;
  source: string;
  why: string;
}

export interface AccessGap {
  field: string;
  ask: string;
  why: string;
}

export interface PrefillResponse {
  form_id: string;
  fields: AccessField[];
  gaps: AccessGap[];
}

export interface AuditLog {
  id: string;
  timestamp: string;
  module: 'GovLens' | 'LexGraph' | 'ForesightOps' | 'AccessBridge';
  user: string;
  action: string;
  latency_ms: number;
  status: 'success' | 'error';
  metadata?: string; // JSON string for storing relevant context
}

// =============================================================================
// ForesightOps Types
// =============================================================================

export type ForesightNodeName =
  | 'parse_request'
  | 'retrieve_assets'
  | 'calculate_risks'
  | 'optimize_allocation'
  | 'synthesize';

export interface ForesightAllocation {
  asset_id: string;
  asset_name: string;
  region: string;
  current_condition: number;
  replacement_cost: number;
  risk_score: number;
  priority_score: number;
  budget_assigned: number;
  status: 'Funded' | 'Deferred' | 'Partial';
  rank: number;
  rationale: string;
}

export interface ForesightRiskScore {
  asset_id: string;
  failure_probability: number;
  impact_score: number;
  risk_score: number;
  risk_category: 'critical' | 'high' | 'medium' | 'low';
  time_to_critical: number | null;
}

export interface ForesightAsset {
  asset_id: string;
  name: string;
  asset_type: string;
  region: string;
  current_condition: number;
  replacement_cost: number;
  age_years: number | null;
  daily_usage: number | null;
  criticality_tier: number | null;
  population_served: number | null;
}

export interface ForesightStepData {
  parse_request: { status: StepStatus; query?: string; };
  retrieve_assets: { status: StepStatus; assets: ForesightAsset[]; assetCount: number; };
  calculate_risks: { status: StepStatus; riskScores: ForesightRiskScore[]; riskDistribution: Record<string, number>; };
  optimize_allocation: { status: StepStatus; allocations: ForesightAllocation[]; totalAllocated: number; assetsFunded: number; };
  synthesize: { status: StepStatus; recommendations: string; confidence: number; };
}

export interface ForesightStreamState {
  trace_log?: string[];
  assets?: ForesightAsset[];
  risk_scores?: ForesightRiskScore[];
  allocations?: ForesightAllocation[];
  total_requested?: number;
  total_allocated?: number;
  assets_funded?: number;
  assets_deferred?: number;
  risk_reduction_pct?: number;
  recommendations?: string;
  confidence_score?: number;
  current_step?: string;
}

export interface ForesightStreamEvent {
  node: ForesightNodeName | 'error';
  state: ForesightStreamState;
}

export interface ForesightResult {
  allocations: ForesightAllocation[];
  totalRequested: number;
  totalAllocated: number;
  assetsFunded: number;
  assetsDeferred: number;
  riskReductionPct: number;
  recommendations: string;
  confidence: number;
}

// =============================================================================
// AccessBridge Types (Enhanced for Streaming Agent)
// =============================================================================

export type AccessBridgeNodeName =
  | 'process_input'
  | 'retrieve_program'
  | 'extract_info'
  | 'analyze_gaps'
  | 'process_follow_up'
  | 'generate_outputs';

export interface ExtractedFieldEnhanced {
  key: string;
  value: unknown;
  source: 'document' | 'voice' | 'text' | 'follow_up';
  confidence: number;
  requires_verification: boolean;
}

export interface InformationGap {
  field: string;
  question: string;
  why_needed: string;
  priority: 'critical' | 'important' | 'optional';
  // For grouped fields (checkbox/radio/dropdown)
  input_type?: 'text' | 'radio' | 'checkbox' | 'dropdown';
  options?: string[];
}

export interface FormFieldGroup {
  group_name: string;
  group_label: string;
  group_type: 'radio' | 'checkbox' | 'dropdown';
  options: Array<{ name: string; label: string }>;
  required: boolean;
  page?: number;
}

export interface AccessBridgeStepData {
  process_input: { status: StepStatus; filesProcessed?: number; };
  retrieve_program: { status: StepStatus; programName?: string; requiredFields?: string[]; };
  extract_info: { status: StepStatus; fieldsExtracted?: number; };
  analyze_gaps: { status: StepStatus; gapsFound?: number; criticalGaps?: number; };
  process_follow_up: { status: StepStatus; answersProcessed?: number; };
  generate_outputs: { status: StepStatus; outputsReady?: string[]; };
}

export interface AccessBridgeStreamState {
  // Input tracking
  document_texts?: string[];
  audio_transcripts?: string[];
  raw_text_input?: string;

  // Context
  program_type?: string;
  program_context?: string;
  required_fields?: string[];
  language?: string;

  // Processing results
  extracted_fields?: ExtractedFieldEnhanced[];
  information_gaps?: InformationGap[];
  follow_up_questions?: string[];
  has_critical_gaps?: boolean;

  // Control
  current_step?: string;
  loop_count?: number;
  trace_log?: string[];

  // Error handling
  message?: string;

  // Outputs
  form_data?: Record<string, { value: unknown; confidence: number; source: string; }>;
  email_draft?: string;
  meeting_prep?: string;
  overall_confidence?: number;
  completion_status?: 'incomplete' | 'needs_input' | 'ready_for_review' | 'complete';
}

export interface AccessBridgeStreamEvent {
  node: AccessBridgeNodeName | 'error';
  state: AccessBridgeStreamState;
}

export interface AccessBridgeResult {
  extractedFields: ExtractedFieldEnhanced[];
  gaps: InformationGap[];
  formData: Record<string, { value: unknown; confidence: number; source: string; }>;
  emailDraft: string;
  meetingPrep: string;
  confidence: number;
  status: 'incomplete' | 'needs_input' | 'ready_for_review' | 'complete';
}