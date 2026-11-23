import { apiFetch } from "./client";
import type { CitationSource, QuestionType } from "@/lib/types";

export interface GeneratedQuestion {
  type: QuestionType;
  topic: string;
  question: string;
  choices: string[];
  reference_answer: string;
  scoring_points: string[];
  max_score: number;
  knowledge_points: string[];
}

export interface TopicProgress {
  topic: string;
  covered_points: string[];
  mastered_points: string[];
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

export function generatePractice(
  topic: string,
  types: string[],
): Promise<PracticeGenerateResponse> {
  return apiFetch<PracticeGenerateResponse>("/api/practice/generate", {
    method: "POST",
    body: { topic, types },
  });
}

export function gradePractice(body: {
  question: string;
  answer: string;
  reference_answer: string;
  scoring_points: string[];
  max_score: number;
}): Promise<PracticeGradingResponse> {
  return apiFetch<PracticeGradingResponse>("/api/practice/runs", {
    method: "POST",
    body,
  });
}

export function savePracticeSession(
  topic: string,
  content: string,
  sources: CitationSource[],
  progress: TopicProgress[],
): Promise<{ session_id: string }> {
  return apiFetch<{ session_id: string }>("/api/practice/sessions", {
    method: "POST",
    body: { topic, content, sources, progress },
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
