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

  it("marks a wrong option incorrect", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "The process identifier inside a communicator",
        reference_answer: COMMA_REFERENCE,
        max_score: 1,
      },
      "The physical core on which a process happens to be scheduled",
      LABELS,
    );

    expect(result?.score).toBe(0);
    expect(result?.explanation).toBe("Incorrect");
  });

  it("sends a key-less single choice to the model grader", () => {
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

    expect(result).toBeNull();
  });

  it("does not trust a negated distractor when the key is missing", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "",
        reference_answer: "The answer is the all-reduce collective, not MPI_Reduce.",
        max_score: 1,
      },
      "MPI_Reduce",
      LABELS,
    );

    expect(result).toBeNull();
  });

  it("does not trust a substring collision when the key is missing", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "",
        reference_answer: "MPI_Allreduce combines values from all ranks.",
        max_score: 1,
      },
      "Reduce",
      LABELS,
    );

    expect(result).toBeNull();
  });

  it("sends a key-less multiple choice to the model grader", () => {
    const result = gradeDeterministic(
      {
        type: "multiple-choice",
        answer: "",
        reference_answer: "Broadcast and Reduce deliver one value.",
        max_score: 2,
      },
      ["Broadcast"],
      LABELS,
    );

    expect(result).toBeNull();
  });

  it("grades multiple choice as an unordered set when the key exists", () => {
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

  it("sends a key-less true or false question to the model grader", () => {
    const result = gradeDeterministic(
      {
        type: "true-false",
        answer: "",
        reference_answer: "True. MPI_COMM_WORLD contains every process.",
        max_score: 1,
      },
      "True",
      LABELS,
    );

    expect(result).toBeNull();
  });

  it("grades true or false when the key exists", () => {
    const result = gradeDeterministic(
      {
        type: "true-false",
        answer: "True",
        reference_answer: "True. MPI_COMM_WORLD contains every process.",
        max_score: 1,
      },
      "False",
      LABELS,
    );

    expect(result?.score).toBe(0);
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
