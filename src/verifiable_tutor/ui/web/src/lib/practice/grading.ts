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
 * Grade a choice question without a model call.
 *
 * The generated question carries the exact correct choice text in "answer".
 * Older questions, and models that omit the field, fall back to matching the
 * chosen option against the reference answer, which is a sentence and may
 * contain commas.
 */
export function gradeDeterministic(
  question: GradeableQuestion,
  selected: string | string[],
  labels: { correct: string; incorrect: string },
): PracticeGradingResponse | null {
  if (!OBJECTIVE_TYPES.includes(question.type)) {
    return null;
  }
  const multiple = question.type === "multiple-choice";
  const chosen = (Array.isArray(selected) ? selected : [selected])
    .map(normalize)
    .filter(Boolean);
  const expected = answerKeys(question.answer, multiple);

  let correct = false;
  if (expected.length > 0) {
    correct =
      chosen.length === expected.length &&
      expected.every((key) => chosen.includes(key));
  } else if (question.type === "true-false") {
    const reference = normalize(question.reference_answer);
    const truth = reference.startsWith("true")
      ? "true"
      : reference.startsWith("false")
        ? "false"
        : "";
    correct = truth !== "" && chosen.length === 1 && chosen[0] === truth;
  } else {
    const reference = normalize(question.reference_answer);
    correct =
      chosen.length > 0 &&
      reference.length > 0 &&
      chosen.every((choice) => reference.includes(choice));
  }

  return {
    score: correct ? question.max_score : 0,
    max_score: question.max_score,
    explanation: correct ? labels.correct : labels.incorrect,
  };
}
