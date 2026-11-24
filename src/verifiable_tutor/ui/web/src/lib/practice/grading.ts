import type { PracticeGradingResponse } from "@/lib/api/practice";
import type { QuestionType } from "@/lib/types";

export interface GradeableQuestion {
  type: QuestionType;
  answer?: string;
  reference_answer: string;
  max_score: number;
}

const OBJECTIVE_TYPES: QuestionType[] = [
  "single-choice",
  "multiple-choice",
  "true-false",
];

function normalize(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/[.;:]+$/, "");
}

function answerKeys(answer: string | undefined, multiple: boolean): string[] {
  if (!answer) return [];
  return (multiple ? answer.split("|") : [answer])
    .map(normalize)
    .filter(Boolean);
}

/**
 * Grade a choice question without a model call, using the exact correct
 * choice text the generator stores in "answer".
 *
 * Questions without that key return null so the model grader decides: the
 * reference answer is a sentence, and substring or negation heuristics let a
 * negated distractor or a partial set earn full marks.
 */
export function gradeDeterministic(
  question: GradeableQuestion,
  selected: string | string[],
  labels: { correct: string; incorrect: string },
): PracticeGradingResponse | null {
  if (!OBJECTIVE_TYPES.includes(question.type)) {
    return null;
  }
  const expected = answerKeys(question.answer, question.type === "multiple-choice");
  if (expected.length === 0) {
    return null;
  }
  const chosen = (Array.isArray(selected) ? selected : [selected])
    .map(normalize)
    .filter(Boolean);
  const correct =
    chosen.length === expected.length &&
    expected.every((key) => chosen.includes(key));

  return {
    score: correct ? question.max_score : 0,
    max_score: question.max_score,
    explanation: correct ? labels.correct : labels.incorrect,
  };
}
