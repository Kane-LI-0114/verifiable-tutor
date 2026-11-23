import { describe, expect, it } from "vitest";

import type { GeneratedQuestion } from "@/lib/api/practice";
import { buildPracticeSummary } from "@/lib/practice/summary";

const LABELS = {
  title: "Practice: {{topic}}",
  total: "**Total: {{score}}/{{max}}**",
  yourAnswer: "Your answer: {{answer}}",
  referenceAnswer: "Reference answer: {{answer}}",
  score: "Score: {{score}}/{{max}}",
  explanation: "Explanation: {{text}}",
  unanswered: "not answered",
};

function question(overrides: Partial<GeneratedQuestion> = {}): GeneratedQuestion {
  return {
    type: "single-choice",
    topic: "MPI",
    question: "What is a rank?",
    choices: ["A", "B"],
    answer: "B",
    reference_answer: "B is the rank.",
    scoring_points: ["rank"],
    max_score: 1,
    knowledge_points: ["processes and ranks"],
    ...overrides,
  };
}

describe("practice summary", () => {
  it("writes the saved summary in the active language", () => {
    const text = buildPracticeSummary({
      topic: "MPI",
      questions: [question(), question({ question: "What is a size?" })],
      answers: ["B", ""],
      results: { 0: { score: 1, max_score: 1, explanation: "Correct" } },
      labels: LABELS,
    });

    expect(text.startsWith("# Practice: MPI")).toBe(true);
    expect(text).toContain("**Total: 1/2**");
    expect(text).toContain("Your answer: B");
    expect(text).toContain("Reference answer: B is the rank.");
    expect(text).toContain("Score: 1/1");
    expect(text).toContain("Explanation: Correct");
    expect(text).toContain("Your answer: not answered");
    expect(text).not.toMatch(/[\u4e00-\u9fff]/);
  });
});
