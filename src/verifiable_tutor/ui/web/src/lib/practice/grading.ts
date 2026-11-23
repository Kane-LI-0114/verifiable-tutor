import type { PracticeGradingResponse } from "@/lib/api/practice";
import type { QuestionType } from "@/lib/types";

export interface GradeableQuestion {
  type: QuestionType;
  answer?: string;
  choices?: string[];
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

function truthOf(reference: string): string {
  const text = normalize(reference);
  if (text.startsWith("true")) return "true";
  if (text.startsWith("false")) return "false";
  return "";
}

/**
 * Grade a choice question without a model call.
 *
 * The generated question carries the exact correct choice text in "answer".
 * Without that field only a single, unambiguous reading is accepted: for a
 * single-choice question, exactly one of the offered choices occurs in the
 * reference answer. Ambiguous cases return null so the model grader decides,
 * because a negated distractor in the reference must never earn full marks.
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

  let correct: boolean | null;
  if (expected.length > 0) {
    correct =
      chosen.length === expected.length &&
      expected.every((key) => chosen.includes(key));
  } else if (multiple) {
    return null;
  } else if (question.type === "true-false") {
    const truth = truthOf(question.reference_answer);
    correct = truth === "" ? null : chosen.length === 1 && chosen[0] === truth;
  } else {
    const reference = normalize(question.reference_answer);
    const mentioned = (question.choices ?? [])
      .map(normalize)
      .filter((choice) => choice.length > 0 && reference.includes(choice));
    if (mentioned.length !== 1) {
      return null;
    }
    correct = chosen.length === 1 && chosen[0] === mentioned[0];
  }

  if (correct === null) {
    return null;
  }
  return {
    score: correct ? question.max_score : 0,
    max_score: question.max_score,
    explanation: correct ? labels.correct : labels.incorrect,
  };
}
