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
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  sequence: number;
  role: "user" | "assistant";
  content: string;
  provider: string | null;
  tier: string | null;
  created_at: string;
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
  step: WorkStepName;
  status: WorkStepStatus;
  detail?: string;
  duration_ms?: number;
  policy?: PolicyState;
  rule_id?: string;
}

export interface ToolCall {
  name: string;
  command: string[];
  exit_code: number | null;
  output: string;
  status: "running" | "done" | "failed";
}

/** Presentation state the assistant turn carries beside its stored content. */
export interface AssistantMeta {
  work_steps: WorkStep[];
  reasoning: string;
  citations: Citation[];
  tool_calls: ToolCall[];
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

export interface EvidencePage {
  doc_id: string;
  page_no: number;
  image_url: string;
  highlights: BboxNorm[];
  quote: string;
}

/** Page-level preview state, selected by the developer controls. */
export type PreviewState = "normal" | "loading" | "empty" | "error";
