import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { Me } from "@/lib/types";

import { createFetchStub, errorResponse, jsonResponse, type StubRoute } from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const STUDENT: Me = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-11-02T12:00:00+00:00",
};

const EMPTY_SESSIONS = { sessions: [] };

function routes(overrides: StubRoute[] = []): StubRoute[] {
  return [
    {
      method: "GET",
      path: "/api/auth/me",
      handler: () => jsonResponse(STUDENT),
    },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse(EMPTY_SESSIONS),
    },
    ...overrides,
  ];
}

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("live session", () => {
  it("bootstraps the session from /api/auth/me and renders the shell", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/chat");

    expect(await screen.findByRole("heading", { name: "Ask a course question" })).toBeInTheDocument();
    expect(stub.calls.filter((call) => call.path === "/api/auth/me")).toHaveLength(1);
  });

  it("redirects an anonymous visitor to the login page with the next path", async () => {
    stub = createFetchStub([
      {
        method: "GET",
        path: "/api/auth/me",
        handler: () => errorResponse("not signed in", 401),
      },
    ]);

    const router = renderLiveRoute("/chat");

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(router.state.location.search).toBe("?next=%2Fchat");
  });

  it("shows a retry state when the backend is unreachable, then recovers", async () => {
    let attempt = 0;
    stub = createFetchStub([
      {
        method: "GET",
        path: "/api/auth/me",
        handler: () => {
          attempt += 1;
          if (attempt === 1) {
            throw new TypeError("fetch failed");
          }
          return jsonResponse(STUDENT);
        },
      },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse(EMPTY_SESSIONS),
      },
    ]);
    const user = userEvent.setup();

    renderLiveRoute("/chat");

    expect(await screen.findByText("The backend is not reachable")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      await screen.findByRole("heading", { name: "Ask a course question" }),
    ).toBeInTheDocument();
  });

  it("signs out through the API and lands on the login page", async () => {
    stub = createFetchStub(
      routes([
        {
          method: "POST",
          path: "/api/auth/logout",
          handler: () => new Response(null, { status: 204 }),
        },
      ]),
    );
    const user = userEvent.setup();

    renderLiveRoute("/chat");

    await user.click(await screen.findByRole("button", { name: "student@ust.hk" }));
    await user.click(screen.getByRole("menuitem", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(
      stub.calls.filter((call) => call.path === "/api/auth/logout"),
    ).toHaveLength(1);
  });
});
