import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { createFetchStub } from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("data mode", () => {
  it("calls the backend from the live app", async () => {
    stub = createFetchStub([
      {
        method: "GET",
        path: "/api/auth/me",
        handler: () =>
          new Response(JSON.stringify({ detail: "not signed in" }), {
            status: 401,
            headers: { "content-type": "application/json" },
          }),
      },
    ]);

    renderLiveRoute("/login");

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(stub.calls[0].path).toBe("/api/auth/me");
  });
});
