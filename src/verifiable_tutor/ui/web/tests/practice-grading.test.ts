import { describe, expect, it } from "vitest";

import { gradeDeterministic } from "@/lib/practice/grading";

const LABELS = { correct: "Correct", incorrect: "Incorrect" };

const CHOICES = [
  "The total number of processes launched by mpiexec",
  "The process identifier inside a communicator",
  "The priority level assigned to a message by the user",
  "The physical core on which a process happens to be scheduled",
];

const COMMA_REFERENCE =
  'The rank is the process identifier inside a communicator: "Rank: process identifier inside a communicator". ' +
  "It is not a core id, not the process count, and not a scheduling priority.";

describe("deterministic practice grading", () => {
  it("marks the chosen option correct when the reference answer contains commas", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "The process identifier inside a communicator",
        choices: CHOICES,
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
        choices: CHOICES,
        reference_answer: COMMA_REFERENCE,
        max_score: 1,
      },
      "The physical core on which a process happens to be scheduled",
      LABELS,
    );

    expect(result?.score).toBe(0);
    expect(result?.explanation).toBe("Incorrect");
  });

  it("uses the only choice the reference mentions when the key is missing", () => {
    const result = gradeDeterministic(
      {
        type: "single-choice",
        answer: "",
        choices: CHOICES,
        reference_answer: COMMA_REFERENCE,
        max_score: 1,
      },
      "The process identifier inside a communicator",
      LABELS,
    );

    expect(result?.score).toBe(1);
  });

  it("does not mark a negated distractor correct without a key", () => {
    const negated =
      "The answer is the process identifier inside a communicator. " +
      "It is not the total number of processes launched by mpiexec.";

    const picked = gradeDeterministic(
      {
        type: "single-choice",
        answer: "",
        choices: CHOICES,
        reference_answer: negated,
        max_score: 1,
      },
      "The total number of processes launched by mpiexec",
      LABELS,
    );
    const ambiguous = gradeDeterministic(
      {
        type: "single-choice",
        answer: "",
        choices: CHOICES,
        reference_answer: negated,
        max_score: 1,
      },
      "The process identifier inside a communicator",
      LABELS,
    );

    expect(picked?.score).not.toBe(1);
    expect(ambiguous).toBeNull();
  });

  it("sends a partial multiple choice without a key to the model grader", () => {
    const result = gradeDeterministic(
      {
        type: "multiple-choice",
        answer: "",
        choices: ["Broadcast", "Reduce", "Scatter"],
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
        choices: ["Broadcast", "Reduce", "Scatter"],
        reference_answer: "Broadcast and Reduce deliver one value.",
        max_score: 2,
      },
      ["Reduce", "Broadcast"],
      LABELS,
    );

    expect(result?.score).toBe(2);
  });

  it("compares true and false without a key", () => {
    const base = {
      type: "true-false" as const,
      answer: "",
      reference_answer: "True. MPI_COMM_WORLD contains every process.",
      max_score: 1,
    };

    expect(gradeDeterministic(base, "True", LABELS)?.score).toBe(1);
    expect(gradeDeterministic(base, "False", LABELS)?.score).toBe(0);
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
