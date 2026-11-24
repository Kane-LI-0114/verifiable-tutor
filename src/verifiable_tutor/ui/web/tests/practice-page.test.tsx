import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import {
  createFetchStub,
  jsonResponse,
  type StubRoute,
} from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const STUDENT = { id: "u1", email: "student@ust.hk", role: "student" };

const CHOICE_QUESTION = {
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
  type: "short-answer" as const,
  question:
    "Explain in one or two sentences why the softmax in attention needs the row maximum.",
  choices: [],
  correct_answer: undefined,
  max_score: 2,
};

let stub: ReturnType<typeof createFetchStub> | null = null;

function routes(generate: () => Response, extra: StubRoute[] = []): StubRoute[] {
  return [
    { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse({ sessions: [] }),
    },
    { method: "POST", path: "/api/practice/generate", handler: generate },
    {
      method: "POST",
      path: "/api/practice/sessions",
      handler: () => jsonResponse({ session_id: "practice-1" }),
    },
    ...extra,
  ];
}

function callsTo(path: string): number {
  return stub === null ? 0 : stub.calls.filter((call) => call.path === path).length;
}

async function chooseTopic(
  user: ReturnType<typeof userEvent.setup>,
  topic: string,
) {
  // The topic control is the only combobox on the page; its label is a
  // sibling of the trigger rather than an associated element.
  await user.click(screen.getByRole("combobox"));
  await user.click(await screen.findByRole("option", { name: topic }));
}

async function generateQuestion(question: unknown) {
  const user = userEvent.setup();
  stub = createFetchStub(
    routes(() =>
      jsonResponse({ questions: [question], sources: [] }),
    ),
  );
  renderLiveRoute("/practice");
  await screen.findByRole("button", { name: "Generate a question" });
  await chooseTopic(user, "MPI");
  await user.click(screen.getByRole("button", { name: "Generate a question" }));
  // The submit control only exists once the questions are on screen.
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
    stub = createFetchStub(routes(() => jsonResponse({ questions: [], sources: [] })));
    renderLiveRoute("/practice");

    const generate = await screen.findByRole("button", {
      name: "Generate a question",
    });
    expect(generate).toBeDisabled();

    await chooseTopic(user, "MPI");

    expect(generate).toBeEnabled();
  });

  it("generates a question for the chosen topic and shows its points", async () => {
    await generateQuestion(CHOICE_QUESTION);

    expect(
      screen.getByText(/Which MPI collective leaves the reduced value/),
    ).toBeInTheDocument();
    expect(screen.getByText("MPI_Allreduce")).toBeInTheDocument();
    expect(screen.getByText("1 point")).toBeInTheDocument();
    expect(callsTo("/api/practice/generate")).toBe(1);
  });

  it("asks for an answer instead of grading an empty submission", async () => {
    const user = await generateQuestion(CHOICE_QUESTION);

    await user.click(screen.getByRole("button", { name: "Submit all answers" }));

    expect(await screen.findByText("Grading")).toBeInTheDocument();
    expect(callsTo("/api/practice/runs")).toBe(0);
    expect(screen.getByText("0/1")).toBeInTheDocument();
  });

  it("grades a single-choice answer without a model call", async () => {
    const user = await generateQuestion(CHOICE_QUESTION);

    await user.click(screen.getByLabelText("MPI_Allreduce"));
    await user.click(screen.getByRole("button", { name: "Submit all answers" }));

    expect(await screen.findByText("Correct")).toBeInTheDocument();
    expect(callsTo("/api/practice/runs")).toBe(0);
    await waitFor(() => expect(callsTo("/api/practice/sessions")).toBe(1));
  });

  it("opens a text area for a short answer question", async () => {
    await generateQuestion(SHORT_QUESTION);

    expect(screen.getByLabelText("Your answer")).toBeInTheDocument();
    expect(screen.getByText("2 points")).toBeInTheDocument();
  });
});
