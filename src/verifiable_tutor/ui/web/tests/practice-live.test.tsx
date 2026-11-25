import { cleanup, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { Me } from "@/lib/types";

import { createFetchStub, jsonResponse, type StubRoute } from "./api-stub";
import { installMemoryStorage } from "./memory-storage";
import { renderLiveRoute } from "./render-live-route";

const STUDENT: Me = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-11-02T12:00:00+00:00",
};

const TRUE_FALSE_QUESTION = {
  type: "true-false",
  topic: "MPI",
  question: "MPI_COMM_WORLD contains every launched process.",
  choices: [],
  answer: "True",
  reference_answer:
    "True. MPI_COMM_WORLD is the default communicator containing all launched processes.",
  scoring_points: ["Names MPI_COMM_WORLD as the default communicator"],
  max_score: 1,
  knowledge_points: ["processes and ranks"],
};

const ROUTES: StubRoute[] = [
  { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
  {
    method: "GET",
    path: "/api/sessions",
    handler: () => jsonResponse({ sessions: [] }),
  },
  {
    method: "POST",
    path: "/api/practice/generate",
    handler: () =>
      jsonResponse({ questions: [TRUE_FALSE_QUESTION], sources: [] }),
  },
];

let stub: ReturnType<typeof createFetchStub> | null = null;

beforeEach(() => {
  installMemoryStorage();
});

afterEach(() => {
  stub?.restore();
  stub = null;
  cleanup();
});

describe("live practice page true/false control", () => {
  it("numbers the question and offers one mutually exclusive True/False choice", async () => {
    const user = userEvent.setup();
    stub = createFetchStub(ROUTES);

    renderLiveRoute("/practice?topic=MPI&types=true-false");

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
  });
});
