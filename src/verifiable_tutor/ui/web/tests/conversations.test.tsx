import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { Conversation } from "@/lib/types";

import { createFetchStub, errorResponse, jsonResponse } from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const ME = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student" as const,
  created_at: "2026-11-02T12:00:00+00:00",
};

const SESSIONS: Conversation[] = [
  {
    id: "sess-1",
    title: "How does MPI_Allreduce work?",
    created_at: "2026-11-03T09:12:00+00:00",
    updated_at: "2026-11-03T09:13:20+00:00",
    message_count: 2,
  },
  {
    id: "sess-2",
    title: "Attention softmax stability",
    created_at: "2026-11-02T14:04:00+00:00",
    updated_at: "2026-11-02T14:06:10+00:00",
    message_count: 2,
  },
];

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("conversation sidebar", () => {
  it("lists the signed-in user's conversations from the API", async () => {
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(ME) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: SESSIONS }),
      },
    ]);

    renderLiveRoute("/chat");

    const history = await screen.findByRole("list", { name: "Conversation history" });
    expect(
      within(history).getByRole("link", { name: "How does MPI_Allreduce work?" }),
    ).toBeInTheDocument();
    expect(
      within(history).getByRole("link", { name: "Attention softmax stability" }),
    ).toBeInTheDocument();
  });

  it("shows the empty state when the account has no conversations", async () => {
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(ME) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: [] }),
      },
    ]);

    renderLiveRoute("/chat");

    expect(await screen.findByText("No conversations yet.")).toBeInTheDocument();
  });

  it("returns to the login page when the conversation list reports an expired session", async () => {
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(ME) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => errorResponse("not authenticated", 401),
      },
    ]);

    const router = renderLiveRoute("/chat");

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(
      screen.queryByText("Could not load the conversations."),
    ).not.toBeInTheDocument();
  });

  it("offers a retry when the conversation list fails to load", async () => {
    let attempt = 0;
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(ME) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => {
          attempt += 1;
          if (attempt === 1) {
            return errorResponse("database is locked", 500);
          }
          return jsonResponse({ sessions: SESSIONS });
        },
      },
    ]);
    const user = userEvent.setup();

    renderLiveRoute("/chat");

    expect(await screen.findByText("Could not load the conversations.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      await screen.findByRole("link", { name: "How does MPI_Allreduce work?" }),
    ).toBeInTheDocument();
    expect(attempt).toBe(2);
  });
});
