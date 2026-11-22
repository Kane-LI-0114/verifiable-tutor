import { apiFetch } from "./client";
import type { CitationSource, QuestionType } from "@/lib/types";

export interface GeneratedQuestion {
  type: QuestionType;
  question: string;
  choices: string[];
  reference_answer: string;
  scoring_points: string[];
  max_score: number;
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
