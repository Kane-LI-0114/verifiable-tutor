import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { PracticeSession } from "@/lib/api/practice";

import {
  createFetchStub,
  jsonResponse,
  type StubRoute,
} from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const STUDENT = { id: "u1", email: "student@ust.hk", role: "student" };

const CHOICE_QUESTION = {
  id: "q1",
  type: "single-choice" as const,
  topic: "MPI",
  question: "Which MPI collective leaves the reduced value on every rank?",
  choices: ["MPI_Allreduce", "MPI_Reduce", "MPI_Bcast"],
  correct_answer: "MPI_Allreduce",
  reference_answer: "MPI_Allreduce leaves the result on every rank.",
  scoring_points: ["names the collective that leaves the result on every rank"],
  max_score: 1,
  knowledge_points: ["collectives"],
};

const SHORT_QUESTION = {
  ...CHOICE_QUESTION,
  id: "q2",
  type: "short-answer" as const,
  question:
    "Explain in one or two sentences why the softmax in attention needs the row maximum.",
  choices: [],
  correct_answer: "",
  max_score: 2,
};

const CREATED_AT = "2026-11-25T09:00:00+00:00";

function session(overrides: Partial<PracticeSession> = {}): PracticeSession {
  const completed = overrides.status === "completed";
  return {
    id: "practice-1",
    title: "MPI 20261125",
    topic: "MPI",
    status: "not_started",
    best_score: completed ? 1 : 0,
    max_score: 3,
    questions: [CHOICE_QUESTION, SHORT_QUESTION],
    sources: [],
    attempts: [
      {
        attempt_no: 1,
        status: completed ? "completed" : "in_progress",
        answers: completed ? { q1: ["MPI_Allreduce"] } : {},
        results: completed
          ? { q1: { score: 1, max_score: 1, explanation: "Correct" } }
          : {},
        score: completed ? 1 : null,
        max_score: 3,
        started_at: CREATED_AT,
        submitted_at: completed ? CREATED_AT : null,
      },
    ],
    created_at: CREATED_AT,
    updated_at: CREATED_AT,
    completed_at: completed ? CREATED_AT : null,
    ...overrides,
  };
}

let stub: ReturnType<typeof createFetchStub> | null = null;

function routes({
  created = session(),
  loaded = session(),
  submitted = session({ status: "completed" }),
  redone = session({ status: "completed" }),
}: {
  created?: PracticeSession;
  loaded?: PracticeSession;
  submitted?: PracticeSession;
  redone?: PracticeSession;
} = {}): StubRoute[] {
  return [
    { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse({ sessions: [] }),
    },
    {
      method: "POST",
      path: "/api/practice/sessions",
      handler: () => jsonResponse(created, { status: 201 }),
    },
    {
      method: "GET",
      path: "/api/practice/sessions/practice-1",
      handler: () => jsonResponse(loaded),
    },
    {
      method: "PATCH",
      path: "/api/practice/sessions/practice-1/attempts/1/answers",
      handler: () => jsonResponse({ status: "in_progress", attempt_no: 1 }),
    },
    {
      method: "POST",
      path: "/api/practice/sessions/practice-1/attempts/1/submit",
      handler: () => jsonResponse(submitted),
    },
    {
      method: "POST",
      path: "/api/practice/sessions/practice-1/attempts",
      handler: () => jsonResponse(redone, { status: 201 }),
    },
    {
      method: "DELETE",
      path: "/api/practice/sessions/practice-1/attempts/1",
      handler: () => new Response(null, { status: 204 }),
    },
  ];
}

function callsTo(method: string, path: string): number {
  return (
    stub?.calls.filter((call) => call.method === method && call.path === path)
      .length ?? 0
  );
}

async function chooseTopic(
  user: ReturnType<typeof userEvent.setup>,
  topic: string,
) {
  await user.click(screen.getByRole("combobox"));
  await user.click(await screen.findByRole("option", { name: topic }));
}

async function generateSession(loaded = session()) {
  const user = userEvent.setup();
  stub = createFetchStub(routes({ loaded }));
  renderLiveRoute("/practice");
  await screen.findByRole("button", { name: "Generate a question" });
  await chooseTopic(user, "MPI");
  await user.click(screen.getByRole("button", { name: "Generate a question" }));
  await screen.findByRole("button", { name: "Open this practice" });
  return user;
}

async function openGenerated(loaded = session()) {
  const user = await generateSession(loaded);
  await user.click(screen.getByRole("button", { name: "Open this practice" }));
  await screen.findByRole("button", { name: "Submit all answers" });
  return user;
}

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("practice page", () => {
  it("keeps generation disabled until a topic is chosen", async () => {
    const user = userEvent.setup();
    stub = createFetchStub(routes());
    renderLiveRoute("/practice");

    const generate = await screen.findByRole("button", {
      name: "Generate a question",
    });
    expect(generate).toBeDisabled();

    await chooseTopic(user, "MPI");

    expect(generate).toBeEnabled();
  });

  it("shows a ready notice and refreshes the practice list after generating", async () => {
    await generateSession();

    expect(screen.getByText("Practice is ready")).toBeInTheDocument();
    expect(
      screen.getByText("It is already in the Practice list on the left."),
    ).toBeInTheDocument();
    expect(callsTo("POST", "/api/practice/sessions")).toBe(1);
    expect(callsTo("GET", "/api/sessions")).toBeGreaterThanOrEqual(2);
  });

  it("opens the generated session from the ready notice", async () => {
    await openGenerated();

    expect(screen.queryByText("Practice is ready")).not.toBeInTheDocument();
    expect(
      screen.getByText(/Which MPI collective leaves the reduced value/),
    ).toBeInTheDocument();
    expect(screen.getByText("MPI_Allreduce")).toBeInTheDocument();
    expect(screen.getByText("1 point")).toBeInTheDocument();
    expect(screen.getByText("Attempt 1/1")).toBeInTheDocument();
    expect(callsTo("GET", "/api/practice/sessions/practice-1")).toBe(1);
  });

  it("autosaves a choice as soon as it is selected", async () => {
    const user = await openGenerated();

    await user.click(screen.getByLabelText("MPI_Allreduce"));

    await waitFor(() =>
      expect(
        callsTo("PATCH", "/api/practice/sessions/practice-1/attempts/1/answers"),
      ).toBe(1),
    );
  });

  it("submits an empty attempt without calling the model grader", async () => {
    const user = await openGenerated();

    await user.click(screen.getByRole("button", { name: "Submit all answers" }));

    expect(
      await screen.findByRole("button", { name: "Practice again" }),
    ).toBeInTheDocument();
    expect(callsTo("POST", "/api/practice/runs")).toBe(0);
    expect(
      callsTo("POST", "/api/practice/sessions/practice-1/attempts/1/submit"),
    ).toBe(1);
  });

  it("grades a single-choice answer without a model call", async () => {
    const user = await openGenerated();

    await user.click(screen.getByLabelText("MPI_Allreduce"));
    await user.click(screen.getByRole("button", { name: "Submit all answers" }));

    expect(await screen.findByText("Correct")).toBeInTheDocument();
    expect(callsTo("POST", "/api/practice/runs")).toBe(0);
    expect(
      callsTo("POST", "/api/practice/sessions/practice-1/attempts/1/submit"),
    ).toBe(1);
  });

  it("opens a text area for a short answer question", async () => {
    await openGenerated();

    expect(screen.getByLabelText("Your answer")).toBeInTheDocument();
    expect(screen.getByText("2 points")).toBeInTheDocument();
  });

  it("renders the choices in the attempt's stored order", async () => {
    const loaded = session();
    loaded.attempts[0].option_orders = {
      q1: ["MPI_Reduce", "MPI_Bcast", "MPI_Allreduce"],
    };
    stub = createFetchStub(routes({ loaded }));
    renderLiveRoute("/practice/practice-1");

    await screen.findByRole("button", { name: "Submit all answers" });

    expect(
      screen.getAllByRole("radio").map((radio) => radio.getAttribute("value")),
    ).toEqual(["MPI_Reduce", "MPI_Bcast", "MPI_Allreduce"]);
  });

  it("deletes only the current attempt", async () => {
    const user = await openGenerated();

    await user.click(screen.getByRole("button", { name: "Delete practice" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(
        callsTo("DELETE", "/api/practice/sessions/practice-1/attempts/1"),
      ).toBe(1),
    );
  });

  it("opens another attempt and pages between them", async () => {
    const user = userEvent.setup();
    const completed = session({ status: "completed" });
    const redone = session({
      status: "completed",
      attempts: [
        completed.attempts[0],
        {
          attempt_no: 2,
          status: "in_progress",
          answers: {},
          results: {},
          score: null,
          max_score: 3,
          started_at: CREATED_AT,
          submitted_at: null,
        },
      ],
    });
    stub = createFetchStub(routes({ loaded: completed, redone }));
    renderLiveRoute("/practice/practice-1");

    await user.click(await screen.findByRole("button", { name: "Practice again" }));

    expect(await screen.findByText("Attempt 2/2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit all answers" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Previous attempt" }));

    expect(await screen.findByText("Attempt 1/2")).toBeInTheDocument();
    expect(await screen.findByText("Correct")).toBeInTheDocument();
  });
});
