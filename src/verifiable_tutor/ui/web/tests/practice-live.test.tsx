import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { Me } from "@/lib/types";

import { createFetchStub, jsonResponse, type StubRoute } from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const STUDENT: Me = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-11-02T12:00:00+00:00",
};

const TRUE_FALSE_QUESTION = {
  id: "q1",
  type: "true-false",
  topic: "MPI",
  question: "MPI_COMM_WORLD contains every launched process.",
  choices: [],
  correct_answer: "True",
  reference_answer:
    "True. MPI_COMM_WORLD is the default communicator containing all launched processes.",
  scoring_points: ["Names MPI_COMM_WORLD as the default communicator"],
  max_score: 1,
  knowledge_points: ["processes and ranks"],
};

const STARTED_AT = "2026-11-25T09:00:00+00:00";

function session(completed = false) {
  return {
    id: "practice-1",
    title: "MPI 20261125",
    topic: "MPI",
    status: completed ? "completed" : "not_started",
    best_score: completed ? 1 : 0,
    max_score: 1,
    questions: [TRUE_FALSE_QUESTION],
    sources: [],
    attempts: [
      {
        attempt_no: 1,
        status: completed ? "completed" : "in_progress",
        answers: completed ? { q1: ["True"] } : {},
        results: completed
          ? { q1: { score: 1, max_score: 1, explanation: "Correct" } }
          : {},
        option_orders: {},
        score: completed ? 1 : null,
        max_score: 1,
        started_at: STARTED_AT,
        submitted_at: completed ? STARTED_AT : null,
      },
    ],
    created_at: STARTED_AT,
    updated_at: STARTED_AT,
    completed_at: completed ? STARTED_AT : null,
  };
}

const ROUTES: StubRoute[] = [
  { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
  {
    method: "GET",
    path: "/api/sessions",
    handler: () => jsonResponse({ sessions: [] }),
  },
  {
    method: "GET",
    path: "/api/practice/sessions/practice-1",
    handler: () => jsonResponse(session()),
  },
  {
    method: "PATCH",
    path: "/api/practice/sessions/practice-1/attempts/1/answers",
    handler: () => jsonResponse({ status: "in_progress", attempt_no: 1 }),
  },
  {
    method: "POST",
    path: "/api/practice/sessions/practice-1/attempts/1/submit",
    handler: () => jsonResponse(session(true)),
  },
];

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
  cleanup();
});

describe("live practice page true/false control", () => {
  it("numbers the question and offers one mutually exclusive True/False choice", async () => {
    const user = userEvent.setup();
    stub = createFetchStub(ROUTES);

    renderLiveRoute("/practice/practice-1");

    expect(await screen.findByText("1.")).toBeInTheDocument();
    const group = await screen.findByRole("radiogroup");
    const trueOption = screen.getByRole("radio", { name: "True" });
    const falseOption = screen.getByRole("radio", { name: "False" });
    expect(group).toContainElement(trueOption);
    expect(group).toContainElement(falseOption);

    await user.click(trueOption);
    expect(trueOption).toBeChecked();
    await user.click(falseOption);
    expect(falseOption).toBeChecked();
    expect(trueOption).not.toBeChecked();

    await user.click(trueOption);
    expect(trueOption).toBeChecked();
    expect(falseOption).not.toBeChecked();

    await user.click(screen.getByRole("button", { name: "Submit all answers" }));

    expect(await screen.findByText("1 of 1")).toBeInTheDocument();
    expect(screen.getByText("Correct")).toBeInTheDocument();
    await waitFor(() =>
      expect(
        stub?.calls.filter((call) => call.method === "PATCH").length,
      ).toBeGreaterThan(0),
    );
  });
});
