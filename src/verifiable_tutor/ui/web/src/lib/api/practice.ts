import { apiFetch } from "./client";
import type { CitationSource, QuestionType } from "@/lib/types";

export interface GeneratedQuestion {
  id: string;
  type: QuestionType;
  topic: string;
  question: string;
  choices: string[];
  correct_answer: string;
  reference_answer: string;
  scoring_points: string[];
  max_score: number;
  knowledge_points: string[];
}

export interface PracticeGenerateResponse {
  questions: GeneratedQuestion[];
  sources: CitationSource[];
}

export interface PracticeGradingResponse {
  score: number;
  max_score: number;
  explanation: string;
}

export type PracticeStatus = "not_started" | "in_progress" | "completed";

export interface PracticeAttempt {
  attempt_no: number;
  status: "in_progress" | "completed";
  answers: Record<string, string[]>;
  results: Record<string, PracticeGradingResponse>;
  option_orders?: Record<string, string[]>;
  score: number | null;
  max_score: number;
  started_at: string;
  submitted_at: string | null;
}

export interface PracticeSession {
  id: string;
  title: string | null;
  topic: string;
  status: PracticeStatus;
  best_score: number;
  max_score: number;
  questions: GeneratedQuestion[];
  sources: CitationSource[];
  attempts: PracticeAttempt[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

/** Generate questions and save the session before the first answer. */
export function createPracticeSession(
  topic: string,
  types: string[],
): Promise<PracticeSession> {
  return apiFetch<PracticeSession>("/api/practice/sessions", {
    method: "POST",
    body: { topic, types },
  });
}

export function getPracticeSession(sessionId: string): Promise<PracticeSession> {
  return apiFetch<PracticeSession>(
    `/api/practice/sessions/${encodeURIComponent(sessionId)}`,
  );
}

export function savePracticeAnswers(
  sessionId: string,
  attemptNo: number,
  answers: Record<string, string[]>,
): Promise<{ status: PracticeStatus; attempt_no: number }> {
  return apiFetch<{ status: PracticeStatus; attempt_no: number }>(
    `/api/practice/sessions/${encodeURIComponent(sessionId)}/attempts/${attemptNo}/answers`,
    { method: "PATCH", body: { answers } },
  );
}

export function submitPracticeAttempt(
  sessionId: string,
  attemptNo: number,
  answers: Record<string, string[]>,
  results: Record<string, PracticeGradingResponse>,
): Promise<PracticeSession> {
  return apiFetch<PracticeSession>(
    `/api/practice/sessions/${encodeURIComponent(sessionId)}/attempts/${attemptNo}/submit`,
    { method: "POST", body: { answers, results } },
  );
}

export function startPracticeAttempt(sessionId: string): Promise<PracticeSession> {
  return apiFetch<PracticeSession>(
    `/api/practice/sessions/${encodeURIComponent(sessionId)}/attempts`,
    { method: "POST" },
  );
}

export function deletePracticeAttempt(
  sessionId: string,
  attemptNo: number,
): Promise<void> {
  return apiFetch<void>(
    `/api/practice/sessions/${encodeURIComponent(sessionId)}/attempts/${attemptNo}`,
    { method: "DELETE" },
  );
}

export function gradePractice(body: {
  question: string;
  answer: string;
  reference_answer: string;
  scoring_points: string[];
  max_score: number;
  sources: CitationSource[];
}): Promise<PracticeGradingResponse> {
  return apiFetch<PracticeGradingResponse>("/api/practice/runs", {
    method: "POST",
    body,
  });
}

export interface ParsePracticeResponse {
  practice: boolean;
  topic: string;
  types: string[];
}

export function parsePractice(message: string): Promise<ParsePracticeResponse> {
  return apiFetch<ParsePracticeResponse>("/api/practice/parse", {
    method: "POST",
    body: { message },
  });
}
