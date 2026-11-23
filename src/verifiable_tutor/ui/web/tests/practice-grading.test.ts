import { describe, expect, it } from "vitest";

import { gradeDeterministic } from "@/lib/practice/grading";

const LABELS = { correct: "Correct", incorrect: "Incorrect" };

const COMMA_REFERENCE =
  'The rank is the process identifier inside a communicator: "Rank: process identifier inside a communicator". ' +
  "It is not a core id, not the process count, and not a scheduling priority.";

describe("deterministic practice grading", () => {
  it("marks the chosen option correct when the reference answer contains commas", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "The process identifier inside a communicator",
        reference_answer: COMMA_REFERENCE,
        max_score: 1,
      },
      "The process identifier inside a communicator",
      LABELS,
    );

    expect(result?.score).toBe(1);
    expect(result?.explanation).toBe("Correct");
  });

  it("falls back to the reference answer when the model omitted the answer key", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "",
        reference_answer: COMMA_REFERENCE,
        max_score: 1,
      },
      "The process identifier inside a communicator",
      LABELS,
    );

    expect(result?.score).toBe(1);
  });

  it("marks a wrong option incorrect", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "The process identifier inside a communicator",
        reference_answer: COMMA_REFERENCE,
        max_score: 1,
      },
      "The physical CPU core the process is pinned to",
      LABELS,
    );

    expect(result?.score).toBe(0);
    expect(result?.explanation).toBe("Incorrect");
  });

  it("grades multiple choice as an unordered set", () => {
    const result = gradeDeterministic(
      {
        type: "multiple-choice",
        answer: "Broadcast | Reduce",
        reference_answer: "Broadcast and Reduce deliver one value.",
        max_score: 2,
      },
      ["Reduce", "Broadcast"],
      LABELS,
    );

    expect(result?.score).toBe(2);
  });

  it("returns null for a short answer so the model grades it", () => {
    const result = gradeDeterministic(
      {
        type: "short-answer",
        answer: "",
        reference_answer: "anything",
        max_score: 5,
      },
      "some text",
      LABELS,
    );

    expect(result).toBeNull();
  });
});
