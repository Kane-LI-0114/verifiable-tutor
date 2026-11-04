import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { ChatMessage, Conversation, Me } from "@/lib/types";

import {
  createFetchStub,
  errorResponse,
  jsonResponse,
  sseResponse,
  type StubRoute,
} from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const STUDENT: Me = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-11-02T12:00:00+00:00",
};

const SESSION_ID = "a1b2c3d4e5f60718293a4b5c6d7e8f90";
const QUESTION = "Why does the softmax in attention subtract the row maximum?";
const STORED_ANSWER = "The stored answer text is hidden while the replay runs.";

const HISTORY: ChatMessage[] = [
  {
    id: "message-user-1",
    sequence: 1,
    role: "user",
    content: QUESTION,
    provider: null,
    tier: null,
    created_at: "2026-11-02T14:04:00+00:00",
    reasoning: null,
    model: null,
    thinking: null,
    work_steps: [],
    citations: [],
    tool_calls: [],
  },
  {
    id: "message-assistant-1",
    sequence: 2,
    role: "assistant",
    content: STORED_ANSWER,
    provider: "deepseek",
    tier: "flash",
    created_at: "2026-11-02T14:04:30+00:00",
    reasoning: null,
    model: null,
    thinking: null,
    work_steps: [],
    citations: [],
    tool_calls: [],
  },
];

const SESSIONS: Conversation[] = [
  {
    id: SESSION_ID,
    title: "Attention softmax stability",
    created_at: "2026-11-02T14:04:00+00:00",
    updated_at: "2026-11-02T14:06:10+00:00",
    message_count: 2,
  },
];

const REPLAY_FRAMES = [
  { type: "start", messageId: "recorded-message" },
  { type: "data-step", data: { step: "generate", status: "started" } },
  { type: "reasoning-start", id: "r1" },
  { type: "reasoning-delta", id: "r1", delta: "Check the row maximum." },
  { type: "reasoning-end", id: "r1" },
  { type: "text-start", id: "t1" },
  { type: "text-delta", id: "t1", delta: "Hel" },
  { type: "text-delta", id: "t1", delta: "lo" },
  { type: "text-end", id: "t1" },
  { type: "data-step", data: { step: "generate", status: "done" } },
  { type: "finish" },
  "[DONE]",
];

const MESSAGES_PATH = /^\/api\/sessions\/[^/]+\/messages$/;
const REPLAY_PATH = /^\/api\/sessions\/[^/]+\/replay$/;

function routes(overrides: StubRoute[] = []): StubRoute[] {
  return [
    { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse({ sessions: SESSIONS }),
    },
    ...overrides,
  ];
}

function history(messages: ChatMessage[] = HISTORY): StubRoute {
  return {
    method: "GET",
    path: MESSAGES_PATH,
    handler: () => jsonResponse({ session_id: SESSION_ID, messages }),
  };
}

function replayRoute(handler: () => Response): StubRoute {
  return { method: "GET", path: REPLAY_PATH, handler };
}

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
});

function replayCalls(): ReturnType<typeof createFetchStub>["calls"] {
  return stub === null ? [] : stub.calls.filter((call) => REPLAY_PATH.test(call.path));
}

function postCalls(): ReturnType<typeof createFetchStub>["calls"] {
  return stub === null ? [] : stub.calls.filter((call) => call.method === "POST");
}

describe("replay", () => {
  it("plays a recorded answer from the replay URL without calling the model", async () => {
    stub = createFetchStub(
      routes([history(), replayRoute(() => sseResponse(REPLAY_FRAMES))]),
    );

    renderLiveRoute(`/chat/${SESSION_ID}?replay=1`);

    expect(
      await screen.findByText("Replaying a recorded session. No model call is made."),
    ).toBeInTheDocument();
    expect(await screen.findByText("Hello")).toBeInTheDocument();
    // The recorded turn carries its own trace: work chain and reasoning.
    expect(screen.getByRole("group", { name: "Work chain" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Reasoning" }));
    expect(await screen.findByText("Check the row maximum.")).toBeInTheDocument();
    // The stored answer text is not shown; only the replays frames fill the turn.
    expect(screen.queryByText(STORED_ANSWER)).not.toBeInTheDocument();
    expect(screen.getByText(QUESTION)).toBeInTheDocument();
    // Replay reads the history and the stream, and never POSTs a chat turn.
    expect(postCalls()).toHaveLength(0);
    expect(replayCalls()).toHaveLength(1);
    expect(replayCalls()[0].url).toContain("speed=1");
    expect(
      stub.calls.filter((call) => MESSAGES_PATH.test(call.path)),
    ).toHaveLength(1);
    // The composer gives way to the replay banner.
    expect(screen.queryByLabelText("Your question")).not.toBeInTheDocument();
  });

  it("keeps the stored provider and tier on a replayed answer", async () => {
    stub = createFetchStub(
      routes([history(), replayRoute(() => sseResponse(REPLAY_FRAMES))]),
    );

    renderLiveRoute(`/chat/${SESSION_ID}?replay=1`);

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    // The persisted answer carries the model that produced it; the replay must
    // not fall back to the literal placeholder badge.
    expect(screen.getByText("deepseek · flash")).toBeInTheDocument();
    expect(screen.queryByText("provider · tier")).not.toBeInTheDocument();
  });

  it("restarts the stream with the new speed", async () => {
    stub = createFetchStub(
      routes([history(), replayRoute(() => sseResponse(REPLAY_FRAMES))]),
    );
    const user = userEvent.setup();

    renderLiveRoute(`/chat/${SESSION_ID}?replay=1`);

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    await user.click(screen.getByRole("combobox", { name: "Speed" }));
    await user.click(await screen.findByRole("option", { name: "2×" }));

    await waitFor(() => expect(replayCalls()).toHaveLength(2));
    expect(replayCalls()[1].url).toContain("speed=2");
    expect(postCalls()).toHaveLength(0);
  });

  it("asks for a conversation when replay has no session id", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/chat?replay=1");

    expect(
      await screen.findByText("Open a conversation before replaying it."),
    ).toBeInTheDocument();
    expect(replayCalls()).toHaveLength(0);
    // The sidebar warms the listed conversations; replay itself asks for none.
    expect(
      stub.calls.filter(
        (call) =>
          MESSAGES_PATH.test(call.path) && !call.path.includes(SESSION_ID),
      ),
    ).toHaveLength(0);
  });

  it("replays an answer when the stored assistant message is missing", async () => {
    // A stopped or failed turn records a start frame but persists no assistant
    // message, so the replay must fill a fresh turn from the frames.
    stub = createFetchStub(
      routes([
        history([HISTORY[0]]),
        replayRoute(() => sseResponse(REPLAY_FRAMES)),
      ]),
    );

    renderLiveRoute(`/chat/${SESSION_ID}?replay=1`);

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Work chain" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("The replay did not load")).not.toBeInTheDocument();
  });

  it("clears the session and returns to sign-in when replay is unauthorized", async () => {
    stub = createFetchStub(
      routes([
        history(),
        replayRoute(() => errorResponse("not signed in", 401)),
      ]),
    );

    renderLiveRoute(`/chat/${SESSION_ID}?replay=1`);

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("The replay did not load"),
    ).not.toBeInTheDocument();
  });

  it("marks the replayed turn as failed when the recorded stream reports an error", async () => {
    stub = createFetchStub(
      routes([
        history(),
        replayRoute(() =>
          sseResponse([
            { type: "start", messageId: "recorded-message" },
            { type: "text-start", id: "t1" },
            { type: "text-delta", id: "t1", delta: "Partial replay" },
            { type: "error", errorText: "recorded failure" },
          ]),
        ),
      ]),
    );

    renderLiveRoute(`/chat/${SESSION_ID}?replay=1`);

    expect(await screen.findByText("The answer stopped")).toBeInTheDocument();
    expect(
      screen.getByText(/The model did not finish this answer/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Partial replay")).not.toBeInTheDocument();
  });

  it("shows the replay failure copy and recovers on retry", async () => {
    let attempt = 0;
    stub = createFetchStub(
      routes([
        history(),
        replayRoute(() => {
          attempt += 1;
          if (attempt === 1) {
            return new Response(JSON.stringify({ detail: "no replay trace" }), {
              status: 404,
              headers: { "content-type": "application/json" },
            });
          }
          return sseResponse(REPLAY_FRAMES);
        }),
      ]),
    );
    const user = userEvent.setup();

    renderLiveRoute(`/chat/${SESSION_ID}?replay=1`);

    expect(await screen.findByText("The replay did not load")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The recorded stream is not available for this conversation.",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(attempt).toBe(2);
  });
});
