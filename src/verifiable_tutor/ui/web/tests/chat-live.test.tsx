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

const SESSION_ID = "6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8";
const NEW_SESSION_ID = "sess-new";
const QUESTION = "How does the halo exchange work?";
const ANSWER = "The halo exchange trades boundary rows between neighboring ranks.";
const FOLLOW_UP = "Why is the row maximum subtracted?";

const HISTORY: ChatMessage[] = [
  {
    id: "message-user-1",
    sequence: 1,
    role: "user",
    content: QUESTION,
    provider: null,
    tier: null,
    created_at: "2026-11-03T09:12:04+00:00",
  },
  {
    id: "message-assistant-1",
    sequence: 2,
    role: "assistant",
    content: ANSWER,
    provider: "deepseek",
    tier: "flash",
    created_at: "2026-11-03T09:13:20+00:00",
  },
];

const SESSIONS: Conversation[] = [
  {
    id: SESSION_ID,
    title: "Halo exchange",
    created_at: "2026-11-03T09:12:00+00:00",
    updated_at: "2026-11-03T09:13:20+00:00",
    message_count: 2,
  },
];

const STREAM_FRAMES = [
  { type: "start", messageId: "streamed-message" },
  { type: "data-step", data: { step: "generate", status: "started" } },
  { type: "text-start", id: "t1" },
  { type: "text-delta", id: "t1", delta: "Hel" },
  { type: "text-delta", id: "t1", delta: "lo" },
  { type: "text-end", id: "t1" },
  { type: "data-step", data: { step: "generate", status: "done" } },
  { type: "finish" },
  "[DONE]",
];

function deferred(): { promise: Promise<void>; resolve: () => void } {
  let resolve!: () => void;
  const promise = new Promise<void>((fulfil) => {
    resolve = fulfil;
  });
  return { promise, resolve };
}

const MESSAGES_PATH = /^\/api\/sessions\/[^/]+\/messages$/;

/** Routes the signed-in shell needs, plus the test-specific handlers. */
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

function historyRoute(
  handler: () => Response | Promise<Response>,
): StubRoute {
  return { method: "GET", path: MESSAGES_PATH, handler };
}

function history(messages: ChatMessage[] = HISTORY): StubRoute {
  return historyRoute(() =>
    jsonResponse({ session_id: SESSION_ID, messages }),
  );
}

function chatRoute(handler: () => Response): StubRoute {
  return { method: "POST", path: "/api/chat", handler };
}

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
});

function postCalls(): ReturnType<typeof createFetchStub>["calls"] {
  return stub === null ? [] : stub.calls.filter((call) => call.method === "POST");
}

function sessionsCalls(): number {
  return stub === null
    ? 0
    : stub.calls.filter((call) => call.path === "/api/sessions").length;
}

describe("live chat", () => {
  it("loads the stored conversation history before the composer", async () => {
    stub = createFetchStub(routes([history()]));

    renderLiveRoute(`/chat/${SESSION_ID}`);

    expect(await screen.findByText(QUESTION)).toBeInTheDocument();
    expect(screen.getByText(ANSWER)).toBeInTheDocument();
    expect(screen.getByLabelText("Your question")).toBeInTheDocument();
    expect(
      stub.calls.filter((call) => MESSAGES_PATH.test(call.path)),
    ).toHaveLength(1);
  });

  it("does not load history for a new conversation", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/chat");

    expect(
      await screen.findByRole("heading", { name: "Ask a course question" }),
    ).toBeInTheDocument();
    expect(stub.calls.filter((call) => MESSAGES_PATH.test(call.path))).toHaveLength(
      0,
    );
  });

  it("offers a new question when the conversation is missing", async () => {
    stub = createFetchStub(
      routes([
        historyRoute(() => errorResponse("conversation not found", 404)),
      ]),
    );

    renderLiveRoute(`/chat/${SESSION_ID}`);

    expect(
      await screen.findByText("This conversation is not available."),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "New question" }).length,
    ).toBeGreaterThan(0);
  });

  it("shows the history failure copy and recovers on retry", async () => {
    let attempt = 0;
    stub = createFetchStub(
      routes([
        historyRoute(() => {
          attempt += 1;
          if (attempt === 1) {
            throw new TypeError("fetch failed");
          }
          return jsonResponse({ session_id: SESSION_ID, messages: HISTORY });
        }),
      ]),
    );
    const user = userEvent.setup();

    renderLiveRoute(`/chat/${SESSION_ID}`);

    expect(
      await screen.findByText("The conversation did not load"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "The conversation could not be loaded. Retry, or start a new question.",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText(QUESTION)).toBeInTheDocument();
    expect(attempt).toBe(2);
  });

  it("sends the question with the selected model and thinking level", async () => {
    stub = createFetchStub(
      routes([
        chatRoute(() =>
          sseResponse(STREAM_FRAMES, {
            headers: { "x-conversation-id": NEW_SESSION_ID },
          }),
        ),
        history(),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/chat");

    const composer = await screen.findByLabelText("Your question");
    await user.type(composer, QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(postCalls()).toHaveLength(1));
    expect(postCalls()[0].body).toEqual({
      message: QUESTION,
      session_id: null,
      provider: "deepseek",
      tier: "flash",
      thinking: "off",
    });

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/chat/${NEW_SESSION_ID}`),
    );
  });

  it("sends the latest model selection and thinking level", async () => {
    stub = createFetchStub(
      routes([
        chatRoute(() =>
          sseResponse(STREAM_FRAMES, {
            headers: { "x-conversation-id": NEW_SESSION_ID },
          }),
        ),
        history(),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/chat");

    const composer = await screen.findByLabelText("Your question");
    await user.type(composer, FOLLOW_UP);
    await user.click(screen.getByRole("button", { name: "Model selection" }));
    await user.click(
      await screen.findByRole("menuitemradio", { name: "MiMo Pro" }),
    );
    await user.click(screen.getByRole("button", { name: "Off" }));
    await user.click(await screen.findByRole("menuitemradio", { name: "High" }));
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(postCalls()).toHaveLength(1));
    expect(postCalls()[0].body).toMatchObject({
      message: FOLLOW_UP,
      provider: "mimo",
      tier: "pro",
      thinking: "high",
    });

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/chat/${NEW_SESSION_ID}`),
    );
  });

  it("streams the answer progressively and then opens the new conversation", async () => {
    const gate = deferred();
    stub = createFetchStub(
      routes([
        chatRoute(() =>
          sseResponse(STREAM_FRAMES, {
            gate: gate.promise,
            headers: { "x-conversation-id": NEW_SESSION_ID },
          }),
        ),
        history(),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/chat");

    const composer = await screen.findByLabelText("Your question");
    await user.type(composer, QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    // The gated stream has delivered only the start frame: the composer shows
    // the stop control and the empty assistant turn shows the generating state.
    expect(
      await screen.findByRole("button", { name: "Stop generating" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Generating the answer"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Hello")).not.toBeInTheDocument();

    gate.resolve();

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Work chain" }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/chat/${NEW_SESSION_ID}`),
    );
    await waitFor(() => expect(sessionsCalls()).toBe(2));
  });

  it("keeps an existing conversation open and refreshes the sidebar", async () => {
    stub = createFetchStub(
      routes([
        history(),
        chatRoute(() =>
          sseResponse(STREAM_FRAMES, {
            headers: { "x-conversation-id": SESSION_ID },
          }),
        ),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute(`/chat/${SESSION_ID}`);

    expect(await screen.findByText(QUESTION)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Your question"), FOLLOW_UP);
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    await waitFor(() => expect(sessionsCalls()).toBe(2));
    expect(router.state.location.pathname).toBe(`/chat/${SESSION_ID}`);
    expect(postCalls()[0].body).toMatchObject({ session_id: SESSION_ID });
  });

  it("keeps the request-time model on a streamed answer when the selector changes", async () => {
    stub = createFetchStub(
      routes([
        history(),
        chatRoute(() =>
          sseResponse(STREAM_FRAMES, {
            headers: { "x-conversation-id": SESSION_ID },
          }),
        ),
      ]),
    );
    const user = userEvent.setup();

    renderLiveRoute(`/chat/${SESSION_ID}`);

    expect(await screen.findByText(QUESTION)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Your question"), FOLLOW_UP);
    await user.click(screen.getByRole("button", { name: "Model selection" }));
    await user.click(
      await screen.findByRole("menuitemradio", { name: "MiMo Pro" }),
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("mimo · pro")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Model selection" }));
    await user.click(
      await screen.findByRole("menuitemradio", { name: "DeepSeek Flash" }),
    );

    // The streamed answer keeps the provider and tier of the request that
    // produced it, not the selector choice made afterwards.
    expect(screen.getByText("mimo · pro")).toBeInTheDocument();
  });

  it("drops the partial answer and returns the question when the stream fails", async () => {
    stub = createFetchStub(
      routes([
        chatRoute(() =>
          sseResponse(
            [
              { type: "start", messageId: "streamed-message" },
              { type: "text-start", id: "t1" },
              { type: "text-delta", id: "t1", delta: "Partial answer" },
              {
                type: "error",
                errorText: "The model failed while answering. Please try again.",
              },
            ],
            { headers: { "x-conversation-id": NEW_SESSION_ID } },
          ),
        ),
      ]),
    );
    const user = userEvent.setup();
    renderLiveRoute("/chat");

    await user.type(await screen.findByLabelText("Your question"), QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("The answer stopped")).toBeInTheDocument();
    expect(
      screen.getByText(/The model did not finish this answer/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Partial answer")).not.toBeInTheDocument();
    expect(postCalls()).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(screen.getByLabelText("Your question")).toHaveValue(QUESTION);
    // Retry fills the composer; it must not resend on its own.
    expect(postCalls()).toHaveLength(1);
  });

  it("retries a failed question in the conversation it already created", async () => {
    let attempt = 0;
    stub = createFetchStub(
      routes([
        chatRoute(() => {
          attempt += 1;
          if (attempt === 1) {
            return new Response(JSON.stringify({ detail: "model busy" }), {
              status: 503,
              headers: {
                "content-type": "application/json",
                "x-conversation-id": NEW_SESSION_ID,
              },
            });
          }
          return sseResponse(STREAM_FRAMES, {
            headers: { "x-conversation-id": NEW_SESSION_ID },
          });
        }),
        history(),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/chat");

    await user.type(await screen.findByLabelText("Your question"), QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText("The model is temporarily unavailable. Try again."),
    ).toBeInTheDocument();
    // The failed turn already persisted a conversation; the sidebar shows it.
    await waitFor(() => expect(sessionsCalls()).toBe(2));
    expect(postCalls()).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(screen.getByLabelText("Your question")).toHaveValue(QUESTION);
    // Retry fills the composer; it must not resend on its own (FR-B12).
    expect(postCalls()).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(postCalls()).toHaveLength(2));
    expect(postCalls()[1].body).toMatchObject({
      message: QUESTION,
      session_id: NEW_SESSION_ID,
    });

    // The retried answer is not dropped: a stale failure flag would remove the
    // assistant turn and skip opening the conversation.
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/chat/${NEW_SESSION_ID}`),
    );
    expect(await screen.findByText(ANSWER)).toBeInTheDocument();
    expect(screen.queryByText("The answer stopped")).not.toBeInTheDocument();
  });

  it("explains that the model is busy when the request fails", async () => {
    stub = createFetchStub(
      routes([chatRoute(() => errorResponse("model busy", 503))]),
    );
    const user = userEvent.setup();
    renderLiveRoute("/chat");

    await user.type(await screen.findByLabelText("Your question"), QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText(
        "The model is temporarily unavailable. Try again.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("The answer stopped")).toBeInTheDocument();
  });

  it("expires the session and returns to sign-in on an unauthorized answer", async () => {
    stub = createFetchStub(
      routes([chatRoute(() => errorResponse("not signed in", 401))]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/chat");

    await user.type(await screen.findByLabelText("Your question"), QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
  });

  it("stops the streaming answer from the composer", async () => {
    const gate = deferred();
    stub = createFetchStub(
      routes([
        chatRoute(() =>
          sseResponse(STREAM_FRAMES, {
            gate: gate.promise,
            headers: { "x-conversation-id": NEW_SESSION_ID },
          }),
        ),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/chat");

    await user.type(await screen.findByLabelText("Your question"), QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    const stop = await screen.findByRole("button", {
      name: "Stop generating",
    });
    await user.click(stop);

    expect(
      await screen.findByRole("button", { name: "Send" }),
    ).toBeInTheDocument();
    expect(postCalls()[0].init.signal?.aborted).toBe(true);
    expect(router.state.location.pathname).toBe("/chat");

    gate.resolve();
  });
});
