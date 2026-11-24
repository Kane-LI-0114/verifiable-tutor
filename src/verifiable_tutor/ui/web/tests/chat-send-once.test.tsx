import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { createFetchStub, jsonResponse, sseResponse } from "./api-stub";
import { installMemoryStorage } from "./memory-storage";
import { renderLiveRoute } from "./render-live-route";

const STUDENT = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-11-02T12:00:00+00:00",
};

const QUESTION = "How does the halo exchange work?";

let stub: ReturnType<typeof createFetchStub> | null = null;

beforeEach(() => {
  installMemoryStorage();
});

afterEach(() => {
  stub?.restore();
  stub = null;
});

function chatRequests(): number {
  return stub === null
    ? 0
    : stub.calls.filter((call) => call.path === "/api/chat").length;
}

describe("composer submit", () => {
  it("sends one turn when send is pressed twice before the first request leaves", async () => {
    // The turn first asks the server whether the text is a practice request, so
    // there is a window where nothing is streaming yet and the send control is
    // still live. Hold that window open and press twice inside it.
    let releaseParse: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      releaseParse = resolve;
    });

    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: [] }),
      },
      {
        method: "POST",
        path: "/api/practice/parse",
        handler: async () => {
          await gate;
          return jsonResponse({ practice: false, topic: "", types: [] });
        },
      },
      {
        method: "POST",
        path: "/api/chat",
        handler: () => sseResponse(["[DONE]"]),
      },
    ]);

    const user = userEvent.setup();
    renderLiveRoute("/chat");

    const composer = await screen.findByRole("textbox");
    await user.type(composer, QUESTION);

    const send = screen.getByRole("button", { name: "Send" });
    await user.click(send);
    await user.click(send);
    releaseParse();

    await waitFor(() => expect(chatRequests()).toBe(1));
  });
});
