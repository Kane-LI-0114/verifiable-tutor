/**
 * Shapes the backend returns, kept in snake case so a page never has to remap
 * a response. Milestone 1 fills them from preview fixtures; milestone 2
 * replaces the source with the HTTP client.
 */

export type Role = "student" | "instructor";

export interface Me {
  id: string;
  email: string;
  role: Role;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  kind?: "chat" | "practice";
  created_at: string;
  updated_at: string;
  message_count: number;
  /** Practice metadata; null or false on chat and legacy practice records. */
  has_practice?: boolean;
  practice_status?: "not_started" | "in_progress" | "completed" | null;
  practice_best_score?: number | null;
  practice_max_score?: number | null;
}

export interface ChatMessage {
  id: string;
  sequence: number;
  role: "user" | "assistant";
  content: string;
  provider: string | null;
  tier: string | null;
  created_at: string;
  /** Persisted turn metadata; user messages carry null and empty values. */
  reasoning: string | null;
  model: string | null;
  thinking: string | null;
  work_steps: WorkStep[];
  citations: Citation[];
  /** Retrieved sources for this answer, in marker order. */
  sources: CitationSource[];
  tool_calls: ToolCall[];
  /** Ordered work-chain events; absent on legacy rows. */
  events?: WorkChainEvent[];
}

export type SourceKind = "course" | "web";

/** One retrieved source behind an answer, keyed by its turn-scoped marker. */
export interface CitationSource {
  marker: number;
  kind: SourceKind;
  title: string;
  summary: string;
  doc_id?: string | null;
  page_no?: number | null;
  url?: string | null;
  chunk_id?: string | null;
}

/** Normalized page box, [x1, y1, x2, y2], from the OCR page record. */
export type BboxNorm = [number, number, number, number];

export interface Citation {
  doc_id: string;
  page_no: number;
  quote: string;
  bbox_norm?: BboxNorm;
}

export interface KnowledgeCard {
  chunk_id: string;
  doc_id: string;
  page_no: number;
  section: string | null;
  summary: string;
  key_terms: string[];
  study_questions: string[];
  citations: Citation[];
  model: string | null;
  prompt_version: string | null;
  build_id: string | null;
  created_at: string | null;
}

export type BuildState = "queued" | "running" | "ready" | "failed";

export interface KnowledgeBuild {
  id: string;
  state: BuildState;
  job_id: string | null;
  records_path: string | null;
  records_count: number | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  request: {
    doc_id?: string;
    max_chunks?: number;
  };
}

/** The five disclosure states from the deadline registry. */
export type PolicyState =
  | "pre-release"
  | "active"
  | "extension-window"
  | "post-deadline"
  | "unknown";

export type WorkStepName =
  | "understand"
  | "retrieve"
  | "verify"
  | "decide"
  | "generate"
  | "cite";

export type WorkStepStatus = "pending" | "started" | "done" | "failed";

export interface WorkStep {
  id: string;
  position?: number;
  step: WorkStepName;
  status: WorkStepStatus;
  detail?: string;
  duration_ms?: number;
  policy?: PolicyState;
  rule_id?: string;
}

export interface ToolCall {
  tool_call_id?: string;
  name: string;
  arguments?: unknown;
  result?: unknown;
  duration_ms?: number;
  command: string[];
  exit_code: number | null;
  output: string | null;
  status: "running" | "done" | "failed";
}

/** One ordered work-chain event: a reasoning segment or a tool call. */
export interface WorkChainEvent {
  kind: "reasoning" | "tool_call";
  reasoning?: string | null;
  step_id?: string | null;
  tool_call?: ToolCall | null;
}

/** Presentation state the assistant turn carries beside its stored content. */
export interface AssistantMeta {
  work_steps: WorkStep[];
  reasoning: string;
  citations: Citation[];
  sources: CitationSource[];
  tool_calls: ToolCall[];
  /** Ordered work-chain events; absent on preview and legacy turns. */
  events?: WorkChainEvent[];
  policy_state: PolicyState;
}

export interface ConversationTurn {
  message: ChatMessage;
  meta?: AssistantMeta;
}

export type QuestionType =
  | "single-choice"
  | "multiple-choice"
  | "true-false"
  | "short-answer"
  | "code";

export interface PracticeChoice {
  value: string;
  label: string;
}

export interface PracticeQuestion {
  id: string;
  type: QuestionType;
  prompt: string;
  choices: PracticeChoice[];
  points: number;
  citations: Citation[];
  code_template?: string;
}

export type Verdict = "correct" | "partial" | "incorrect";

export interface TestCase {
  name: string;
  status: "passed" | "failed";
  duration_ms?: number;
  message?: string;
}

export interface TestSuite {
  name: string;
  cases: TestCase[];
}

export interface GradingResult {
  question_id: string;
  score: number;
  max_score: number;
  verdict: Verdict;
  explanation: string;
  citations: Citation[];
  test_suites?: TestSuite[];
}

export interface DeadlineEntry {
  id: string;
  title: string;
  release: string;
  due: string;
  extension_until: string | null;
  state: PolicyState;
}

export interface DeadlineRegistry {
  version: string;
  clock: string;
  entries: DeadlineEntry[];
}

/** Page-level preview state, selected by the developer controls. */
export type PreviewState = "normal" | "loading" | "empty" | "error";
