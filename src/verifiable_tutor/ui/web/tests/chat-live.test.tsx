import { act, cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type {
  ChatMessage,
  Citation,
  CitationSource,
  Conversation,
  Me,
  ToolCall,
  WorkStep,
} from "@/lib/types";

import {
  createFetchStub,
  errorResponse,
  jsonResponse,
  sseResponse,
  type FetchCall,
  type StubRoute,
} from "./api-stub";
import { installMemoryStorage } from "./memory-storage";
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

const STORED_REASONING =
  "The stored trace explains how the halo exchange answer was reached.";
const STORED_STEP_DETAIL = "Parsed the halo exchange question.";
const STORED_CITATION: Citation = {
  doc_id: "ACS_lecture_2_2026F",
  page_no: 12,
  quote:
    "MPI_Allreduce combines values from all ranks and distributes the result to all ranks.",
  bbox_norm: [0.08, 0.22, 0.9, 0.3],
};

const STORED_SOURCES: CitationSource[] = [
  {
    marker: 1,
    kind: "course",
    title: "Lecture 2: Collectives",
    summary: "MPI_Allreduce combines values from all ranks.",
    doc_id: "ACS_lecture_2_2026F",
    page_no: 12,
    url: null,
  },
];
const STORED_TOOL_CALL: ToolCall = {
  name: "course_search",
  command: ["course_search", "--query", "halo exchange", "--top-k", "5"],
  exit_code: 0,
  output: "ACS_lecture_2_2026F p.12 (0.84)",
  status: "done",
};
const STORED_STEPS: WorkStep[] = [
  {
    id: "understand",
    step: "understand",
    status: "done",
    duration_ms: 320,
    detail: STORED_STEP_DETAIL,
  },
  { id: "retrieve", step: "retrieve", status: "done", duration_ms: 1180 },
  {
    id: "decide",
    step: "decide",
    status: "done",
    duration_ms: 12,
    policy: "post-deadline",
    rule_id: "post-deadline.hint-only",
  },
  { id: "generate", step: "generate", status: "done", duration_ms: 2400 },
];

/** The null and empty metadata a user message persists with. */
function noTurnMeta() {
  return {
    reasoning: null,
    model: null,
    thinking: null,
    work_steps: [] as WorkStep[],
    citations: [] as Citation[],
    sources: [] as CitationSource[],
    tool_calls: [] as ToolCall[],
  };
}

const HISTORY: ChatMessage[] = [
  {
    id: "message-user-1",
    sequence: 1,
    role: "user",
    content: QUESTION,
    provider: null,
    tier: null,
    created_at: "2026-11-03T09:12:04+00:00",
    ...noTurnMeta(),
  },
  {
    id: "message-assistant-1",
    sequence: 2,
    role: "assistant",
    content: ANSWER,
    provider: "deepseek",
    tier: "flash",
    created_at: "2026-11-03T09:13:20+00:00",
    reasoning: STORED_REASONING,
    model: "deepseek-flash",
    thinking: "high",
    work_steps: STORED_STEPS,
    citations: [STORED_CITATION],
    sources: STORED_SOURCES,
    tool_calls: [STORED_TOOL_CALL],
    events: [
      { kind: "reasoning", reasoning: STORED_REASONING, step_id: "retrieve" },
      {
        kind: "tool_call",
        tool_call: STORED_TOOL_CALL,
        step_id: "retrieve",
      },
    ],
  },
];

/**
 * The history a finished first answer becomes: the backend stores the streamed
 * answer with the id the stream announced and the work steps it emitted.
 */
const NEW_HISTORY: ChatMessage[] = [
  {
    id: "message-user-new",
    sequence: 1,
    role: "user",
    content: QUESTION,
    provider: null,
    tier: null,
    created_at: "2026-11-03T10:00:00+00:00",
    ...noTurnMeta(),
  },
  {
    id: "streamed-message",
    sequence: 2,
    role: "assistant",
    content: "Hello",
    provider: "deepseek",
    tier: "flash",
    created_at: "2026-11-03T10:00:01+00:00",
    reasoning: null,
    model: "deepseek-flash",
    thinking: "off",
    work_steps: [{ id: "generate", step: "generate", status: "done", duration_ms: 120 }],
    citations: [],
    sources: [],
    tool_calls: [],
  },
];

/** An answer persisted before turn metadata existed: its text, and nothing else. */
const LEGACY_ANSWER = "The legacy answer predates persisted turn metadata.";

const LEGACY_HISTORY: ChatMessage[] = [
  {
    id: "legacy-user",
    sequence: 1,
    role: "user",
    content: QUESTION,
    provider: null,
    tier: null,
    created_at: "2026-11-01T09:00:00+00:00",
    ...noTurnMeta(),
  },
  {
    id: "legacy-assistant",
    sequence: 2,
    role: "assistant",
    content: LEGACY_ANSWER,
    provider: "deepseek",
    tier: "flash",
    created_at: "2026-11-01T09:00:30+00:00",
    ...noTurnMeta(),
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

const TOOL_STREAM_FRAMES = [
  { type: "start", messageId: "streamed-tool-message" },
  { type: "data-step", data: { step: "generate", status: "started" } },
  { type: "start-step" },
  { type: "reasoning-start", id: "r1" },
  { type: "reasoning-delta", id: "r1", delta: "First, search the course." },
  { type: "reasoning-end", id: "r1" },
  {
    type: "data-tool",
    data: {
      tool_call_id: "call_1",
      name: "search_course",
      status: "running",
      step_id: "retrieve",
      arguments: { query: "MPI_Allreduce" },
    },
  },
  { type: "data-step", data: { step: "retrieve", status: "started" } },
  {
    type: "data-tool",
    data: {
      tool_call_id: "call_1",
      name: "search_course",
      status: "done",
      step_id: "retrieve",
      arguments: { query: "MPI_Allreduce" },
      output: "1 course chunks",
      duration_ms: 42,
    },
  },
  {
    type: "data-sources",
    data: {
      sources: [
        {
          marker: 1,
          kind: "course",
          title: "Tutorial 2: Collectives",
          summary: "MPI_Allreduce reduces a value across all ranks.",
          doc_id: "Tutorial_2",
          page_no: 8,
          url: null,
          chunk_id: "Tutorial_2:p008:c00",
        },
      ],
    },
  },
  { type: "data-step", data: { step: "retrieve", status: "done" } },
  { type: "finish-step" },
  { type: "start-step" },
  { type: "text-start", id: "t1" },
  { type: "text-delta", id: "t1", delta: "Allreduce sums a value." },
  { type: "text-end", id: "t1" },
  { type: "finish-step" },
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
  handler: (call: FetchCall) => Response | Promise<Response>,
): StubRoute {
  return { method: "GET", path: MESSAGES_PATH, handler };
}

function history(messages: ChatMessage[] = HISTORY): StubRoute {
  return historyRoute((call) => {
    const isNew = call.path === `/api/sessions/${NEW_SESSION_ID}/messages`;
    return jsonResponse({
      session_id: isNew ? NEW_SESSION_ID : SESSION_ID,
      messages: isNew ? NEW_HISTORY : messages,
    });
  });
}

function chatRoute(handler: () => Response | Promise<Response>): StubRoute {
  return { method: "POST", path: "/api/chat", handler };
}

let stub: ReturnType<typeof createFetchStub> | null = null;

beforeEach(() => {
  // The composer remembers its selection in local storage; install a working
  // store and start every test from the defaults.
  installMemoryStorage();
});

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

function messageCalls(sessionId: string): number {
  return stub === null
    ? 0
    : stub.calls.filter(
        (call) => call.path === `/api/sessions/${sessionId}/messages`,
      ).length;
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
    // The sidebar warms the listed conversations; the new chat loads none of
    // its own history because it has no conversation yet.
    expect(
      stub.calls.filter(
        (call) =>
          MESSAGES_PATH.test(call.path) && !call.path.includes(SESSION_ID),
      ),
    ).toHaveLength(0);
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
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
      // No sidebar conversations, so the retry below is the only history load.
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: [] }),
      },
      historyRoute(() => {
        attempt += 1;
        if (attempt === 1) {
          throw new TypeError("fetch failed");
        }
        return jsonResponse({ session_id: SESSION_ID, messages: HISTORY });
      }),
    ]);
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
    // MiMo exposes on and off only; it has no effort levels.
    expect(
      await screen.findByRole("menuitemradio", { name: "On" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("menuitemradio", { name: "Low" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("menuitemradio", { name: "Max" }),
    ).not.toBeInTheDocument();
    await user.click(await screen.findByRole("menuitemradio", { name: "On" }));
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(postCalls()).toHaveLength(1));
    expect(postCalls()[0].body).toMatchObject({
      message: FOLLOW_UP,
      provider: "mimo",
      tier: "pro",
      thinking: "on",
    });

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/chat/${NEW_SESSION_ID}`),
    );
  });

  it("keeps the chosen model and thinking level across a reload and another conversation", async () => {
    const secondSessionId = "second-session";
    const secondSession: Conversation = {
      id: secondSessionId,
      title: "Another conversation",
      created_at: "2026-11-03T11:00:00+00:00",
      updated_at: "2026-11-03T11:01:00+00:00",
      message_count: 2,
    };
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: [...SESSIONS, secondSession] }),
      },
      historyRoute((call) =>
        jsonResponse({
          session_id: call.path.split("/")[3],
          messages: HISTORY,
        }),
      ),
    ]);
    const user = userEvent.setup();
    renderLiveRoute(`/chat/${SESSION_ID}`);
    await screen.findByText(QUESTION);

    // Defaults until the user chooses.
    expect(
      screen.getByRole("button", { name: "Model selection" }),
    ).toHaveTextContent("DeepSeek Flash");
    expect(screen.getByRole("button", { name: "Off" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Model selection" }));
    await user.click(
      await screen.findByRole("menuitemradio", { name: "MiMo Pro" }),
    );
    await user.click(screen.getByRole("button", { name: "Off" }));
    await user.click(await screen.findByRole("menuitemradio", { name: "On" }));

    // A refresh remounts the route; the last selection comes back.
    cleanup();
    renderLiveRoute(`/chat/${SESSION_ID}`);
    expect(await screen.findByText(QUESTION)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Model selection" }),
    ).toHaveTextContent("MiMo Pro");
    expect(screen.getByRole("button", { name: "On" })).toBeInTheDocument();

    // Switching to another conversation keeps the same last selection.
    cleanup();
    renderLiveRoute(`/chat/${secondSessionId}`);
    expect(await screen.findByText(QUESTION)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Model selection" }),
    ).toHaveTextContent("MiMo Pro");
    expect(screen.getByRole("button", { name: "On" })).toBeInTheDocument();

    // A new conversation keeps the last choice too.
    cleanup();
    renderLiveRoute("/chat");
    expect(await screen.findByLabelText("Your question")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Model selection" }),
    ).toHaveTextContent("MiMo Pro");
    expect(screen.getByRole("button", { name: "On" })).toBeInTheDocument();
  });

  it("shows a pending answer from the moment the question is sent", async () => {
    const answering = deferred();
    stub = createFetchStub(
      routes([
        chatRoute(async () => {
          await answering.promise;
          return sseResponse(STREAM_FRAMES, {
            headers: { "x-conversation-id": NEW_SESSION_ID },
          });
        }),
        history(),
      ]),
    );
    const user = userEvent.setup();
    renderLiveRoute("/chat");

    const composer = await screen.findByLabelText("Your question");
    await user.type(composer, QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    // The request is in flight and no frame has arrived, so the thread holds a
    // place for the answer instead of staying blank until the first token.
    expect(await screen.findByText("Generating the answer")).toBeInTheDocument();
    expect(
      document.querySelector('[data-slot="answer-pending"]'),
    ).not.toBeNull();
    expect(screen.getByText(QUESTION)).toBeInTheDocument();
    expect(screen.queryByText("Hello")).not.toBeInTheDocument();

    answering.resolve();

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(
      document.querySelector('[data-slot="answer-pending"]'),
    ).toBeNull();
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

  it("renders the persisted work chain when the first answer opens the conversation", async () => {
    const gate = deferred();
    stub = createFetchStub(
      routes([
        chatRoute(() =>
          sseResponse(STREAM_FRAMES, {
            headers: { "x-conversation-id": NEW_SESSION_ID },
          }),
        ),
        historyRoute(async (call) => {
          if (call.path !== `/api/sessions/${NEW_SESSION_ID}/messages`) {
            return jsonResponse({ session_id: SESSION_ID, messages: HISTORY });
          }
          await gate.promise;
          return jsonResponse({
            session_id: NEW_SESSION_ID,
            messages: NEW_HISTORY,
          });
        }),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/chat");

    const composer = await screen.findByLabelText("Your question");
    await user.type(composer, QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    // The finished stream is what opens the conversation, so the new route is
    // the marker for "the first answer completed".
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/chat/${NEW_SESSION_ID}`),
    );

    // The reopened conversation loads the persisted turn; it does not inherit
    // the finished stream. While the history is pending there is no work chain.
    await waitFor(() => expect(messageCalls(NEW_SESSION_ID)).toBe(1));
    expect(
      screen.queryByRole("group", { name: "Work chain" }),
    ).not.toBeInTheDocument();

    gate.resolve();

    // The stored row carries the streamed answer and the generate step, so the
    // work chain renders from persisted metadata, not from data-step parts.
    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Work chain" })).toBeInTheDocument();
    expect(screen.getByText("1 of 1 steps complete")).toBeInTheDocument();
  });

  it("renders the stored work chain, thinking, citations, and tool calls of a conversation", async () => {
    stub = createFetchStub(routes([history()]));
    const user = userEvent.setup();

    renderLiveRoute(`/chat/${SESSION_ID}`);

    // The answer text and the turn trace both come from the stored message.
    expect(await screen.findByText(ANSWER)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Work chain" })).toBeInTheDocument();
    expect(screen.getByText("4 of 4 steps complete")).toBeInTheDocument();
    // The policy state of the persisted decide step labels the work chain.
    expect(screen.getAllByText("Post-deadline").length).toBeGreaterThan(0);
    const capsules = screen.getAllByRole("button", {
      name: /Show this answer's citation sources/,
    });
    const capsule = capsules[capsules.length - 1];
    expect(capsule).toHaveTextContent("1 course page");

    await user.click(capsule);

    const pane = await screen.findByTestId("source-pane");
    expect(within(pane).getByText("Lecture 2: Collectives")).toBeInTheDocument();

    // The work chain expands to one section per persisted step. Understand
    // and decide have no events, but their sections still render.
    await user.click(screen.getByRole("button", { name: /Work chain/ }));
    expect(screen.getByText("Understand the question")).toBeInTheDocument();
    expect(screen.getByText("Retrieve course pages")).toBeInTheDocument();
    expect(screen.getByText("Apply the disclosure policy")).toBeInTheDocument();
    expect(screen.getByText("Write the answer")).toBeInTheDocument();
    expect(screen.queryByText("Verify quoted spans")).not.toBeInTheDocument();
    expect(screen.queryByText("Attach citations")).not.toBeInTheDocument();
    expect(screen.getByText(STORED_STEP_DETAIL)).toBeInTheDocument();
    expect(
      screen.getByTitle(/post-deadline\.hint-only/),
    ).toBeInTheDocument();

    const retrieve = screen.getByRole("region", {
      name: /Retrieve course pages/,
    });
    expect(within(retrieve).getByText("Tool call: course_search")).toBeInTheDocument();
    expect(within(retrieve).getByText(STORED_REASONING)).toBeInTheDocument();
  });

  it("renders a legacy answer without a work chain or thinking region", async () => {
    stub = createFetchStub(routes([history(LEGACY_HISTORY)]));

    renderLiveRoute(`/chat/${SESSION_ID}`);

    // An answer persisted before turn metadata existed has text but no trace
    // to show, so no empty work chain or thinking region is rendered for it.
    expect(await screen.findByText(LEGACY_ANSWER)).toBeInTheDocument();
    expect(
      screen.queryByRole("group", { name: "Work chain" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Reasoning" }),
    ).not.toBeInTheDocument();
  });

  it("restores each conversation's own scroll position after a reload", async () => {
    const secondSessionId = "second-session";
    const secondSession: Conversation = {
      id: secondSessionId,
      title: "Another conversation",
      created_at: "2026-11-03T11:00:00+00:00",
      updated_at: "2026-11-03T11:01:00+00:00",
      message_count: 2,
    };
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: [...SESSIONS, secondSession] }),
      },
      historyRoute((call) =>
        jsonResponse({
          session_id: call.path.split("/")[3],
          messages: HISTORY,
        }),
      ),
    ]);

    async function viewport(): Promise<HTMLElement> {
      await screen.findByText(QUESTION);
      const element = document.querySelector<HTMLElement>(
        '[data-slot="message-scroller-viewport"]',
      );
      expect(element).not.toBeNull();
      return element as HTMLElement;
    }

    function scrollTo(element: HTMLElement, top: number) {
      Object.defineProperty(element, "scrollHeight", {
        configurable: true,
        value: 1000,
      });
      Object.defineProperty(element, "clientHeight", {
        configurable: true,
        value: 400,
      });
      // A real gesture marks the intent; the shell only remembers user scrolls.
      fireEvent.wheel(element);
      element.scrollTop = top;
      fireEvent.scroll(element);
    }

    renderLiveRoute(`/chat/${SESSION_ID}`);
    scrollTo(await viewport(), 120);
    cleanup();

    renderLiveRoute(`/chat/${secondSessionId}`);
    scrollTo(await viewport(), 40);
    cleanup();

    // Reopening a conversation restores the position the reader left it at.
    renderLiveRoute(`/chat/${SESSION_ID}`);
    const first = await viewport();
    await waitFor(() => expect(first.scrollTop).toBe(120));
    // The scroller's own programmatic positioning must not overwrite it.
    first.scrollTop = 0;
    fireEvent.scroll(first);
    cleanup();

    renderLiveRoute(`/chat/${SESSION_ID}`);
    const reopened = await viewport();
    await waitFor(() => expect(reopened.scrollTop).toBe(120));
    cleanup();

    renderLiveRoute(`/chat/${secondSessionId}`);
    const second = await viewport();
    await waitFor(() => expect(second.scrollTop).toBe(40));
  });

  it("revisits a conversation from cache without a loading flash", async () => {
    const secondSessionId = "second-session";
    const secondSession: Conversation = {
      id: secondSessionId,
      title: "Another conversation",
      created_at: "2026-11-03T11:00:00+00:00",
      updated_at: "2026-11-03T11:01:00+00:00",
      message_count: 2,
    };
    let releaseSecond: (() => void) | null = null;
    const secondHistory = new Promise<void>((resolve) => {
      releaseSecond = resolve;
    });
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: [...SESSIONS, secondSession] }),
      },
      historyRoute(async (call) => {
        if (call.path.includes(secondSessionId)) {
          await secondHistory;
        }
        return jsonResponse({
          session_id: call.path.split("/")[3],
          messages: HISTORY,
        });
      }),
    ]);
    const router = renderLiveRoute(`/chat/${SESSION_ID}`);
    expect(await screen.findByText(QUESTION)).toBeInTheDocument();

    // First visit to another conversation still shows the loading state.
    await act(async () => {
      await router.navigate(`/chat/${secondSessionId}`);
    });
    expect(
      screen.getByRole("status", { name: "Loading" }),
    ).toBeInTheDocument();
    await act(async () => {
      releaseSecond?.();
    });
    expect(await screen.findByText(QUESTION)).toBeInTheDocument();

    // Switching back renders the cached conversation immediately.
    await act(async () => {
      await router.navigate(`/chat/${SESSION_ID}`);
    });
    expect(
      screen.queryByRole("status", { name: "Loading" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(QUESTION)).toBeInTheDocument();
  });

  it("prefetches the sidebar conversations so switching has no loading flash", async () => {
    const secondSessionId = "prefetch-session";
    const secondSession: Conversation = {
      id: secondSessionId,
      title: "Prefetched conversation",
      created_at: "2026-11-03T11:00:00+00:00",
      updated_at: "2026-11-03T11:01:00+00:00",
      message_count: 2,
    };
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
      {
        method: "GET",
        path: "/api/sessions",
        handler: () => jsonResponse({ sessions: [...SESSIONS, secondSession] }),
      },
      historyRoute(async (call) => {
        if (call.path.includes(secondSessionId)) {
          await new Promise((resolve) => setTimeout(resolve, 40));
        }
        return jsonResponse({
          session_id: call.path.split("/")[3],
          messages: HISTORY,
        });
      }),
    ]);
    const router = renderLiveRoute(`/chat/${SESSION_ID}`);
    expect(await screen.findByText(QUESTION)).toBeInTheDocument();

    await waitFor(() => expect(messageCalls(secondSessionId)).toBe(1));
    // Let the warm-up land in the cache before the reader opens it.
    await new Promise((resolve) => setTimeout(resolve, 60));

    await act(async () => {
      await router.navigate(`/chat/${secondSessionId}`);
    });

    expect(
      screen.queryByRole("status", { name: "Loading" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(QUESTION)).toBeInTheDocument();
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
    // assistant turn and skip opening the conversation. The reopened
    // conversation loads the persisted turn, which carries the streamed answer.
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/chat/${NEW_SESSION_ID}`),
    );
    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Work chain" }),
    ).toBeInTheDocument();
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
  it("renders a live tool call from the data-tool frames", async () => {
    stub = createFetchStub(
      routes([
        chatRoute(() =>
          sseResponse(TOOL_STREAM_FRAMES, {
            headers: { "x-conversation-id": SESSION_ID },
          }),
        ),
        history(),
      ]),
    );
    const user = userEvent.setup();
    renderLiveRoute(`/chat/${SESSION_ID}`);

    await user.type(await screen.findByLabelText("Your question"), QUESTION);
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Allreduce sums a value.")).toBeInTheDocument();

    const capsules = screen.getAllByRole("button", {
      name: /Show this answer's citation sources/,
    });
    const capsule = capsules[capsules.length - 1];
    expect(capsule).toHaveTextContent("1 course page");

    await user.click(capsule);

    const pane = await screen.findByTestId("source-pane");
    expect(within(pane).getByText("Tutorial 2: Collectives")).toBeInTheDocument();
    await user.click(
      within(pane).getByRole("button", { name: "Collapse citation sources" }),
    );

    // The live tool call is inside the live work chain; the stored turn has its own.
    const workChains = screen.getAllByRole("button", { name: /Work chain/ });
    await user.click(workChains[workChains.length - 1]);
    const toolCall = await screen.findByText("Tool call: search_course");
    // The reasoning and the tool call live under their own step sections.
    const retrieve = screen.getByRole("region", {
      name: /Retrieve course pages/,
    });
    expect(within(retrieve).getByText("Tool call: search_course")).toBeInTheDocument();
    expect(within(retrieve).getByText("First, search the course.")).toBeInTheDocument();
    await user.click(toolCall);
    expect(await screen.findByText("Arguments")).toBeInTheDocument();
    expect(await screen.findByText("1 course chunks")).toBeInTheDocument();
    expect(await screen.findByText("Duration 42 ms")).toBeInTheDocument();
  });
});
