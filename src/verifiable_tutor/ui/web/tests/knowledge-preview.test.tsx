import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createFetchStub, jsonResponse, sseResponse, type StubRoute } from "./api-stub";
import { installMemoryStorage } from "./memory-storage";
import { renderLiveRoute } from "./render-live-route";
import { clearDocumentPath } from "@/lib/knowledge/return-path";

// pdf.js needs a worker and a real canvas; the page's own controls are what
// this seam tests, so the renderer is replaced with a resolving stub.
vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  getDocument: () => ({
    promise: Promise.resolve({
      numPages: 67,
      getPage: async () => ({
        getViewport: () => ({ width: 120, height: 90 }),
        render: () => ({ promise: Promise.resolve() }),
      }),
    }),
  }),
}));
vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({ default: "" }));

const STUDENT = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-11-02T12:00:00+00:00",
};

const DOCUMENT = {
  id: "ACS_Lecture_1_2026F",
  title: "ACS_Lecture_1_2026F",
  filename: "ACS_Lecture_1_2026F.pdf",
  folder_id: "f-lectures",
  page_count: 67,
  chunk_count: 71,
  byte_size: 10470744,
  status: "ready",
  status_detail: null,
  summary: "A lecture on GPU architecture and CUDA execution.",
  summary_model: "qwen3.8-27b",
  created_at: "2026-11-05T04:00:00+00:00",
  indexed_at: "2026-11-05T04:20:00+00:00",
  pdf_url: "/api/knowledge/documents/ACS_Lecture_1_2026F/file",
  thumbnail_url: "/api/corpus/ACS_Lecture_1_2026F/pages/1.webp",
};

const STREAM_FRAMES = [
  { type: "start", messageId: "answer-1" },
  { type: "text-start", id: "t1" },
  { type: "text-delta", id: "t1", delta: "This slide covers the GPU memory hierarchy." },
  { type: "text-end", id: "t1" },
  { type: "finish" },
  "[DONE]",
];

let stub: ReturnType<typeof createFetchStub> | null = null;

/** A promise the test resolves when it wants the held request to answer. */
function deferred(): { promise: Promise<void>; resolve: () => void } {
  let resolve!: () => void;
  const promise = new Promise<void>((fulfil) => {
    resolve = fulfil;
  });
  return { promise, resolve };
}

function routes(overrides: StubRoute[] = []): StubRoute[] {
  return [
    { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse({ sessions: [] }),
    },
    {
      method: "GET",
      path: "/api/knowledge/documents/ACS_Lecture_1_2026F/file",
      handler: () =>
        new Response(new Uint8Array([37, 80, 68, 70]).buffer, {
          status: 200,
          headers: { "content-type": "application/pdf" },
        }),
    },
    {
      method: "GET",
      path: "/api/knowledge/documents/ACS_Lecture_1_2026F",
      handler: () => jsonResponse(DOCUMENT),
    },
    ...overrides,
  ];
}

beforeEach(() => {
  installMemoryStorage();
  clearDocumentPath();
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
  })) as never;
});

afterEach(() => {
  stub?.restore();
  stub = null;
});

const STORED_TURNS = [
  {
    id: "stored-question",
    sequence: 1,
    role: "user",
    content: "What is on this page?",
    provider: null,
    tier: null,
    created_at: "2026-11-13T08:00:00+00:00",
    reasoning: null,
    model: null,
    thinking: null,
    work_steps: [],
    citations: [],
    sources: [],
    tool_calls: [],
  },
  {
    id: "stored-answer",
    sequence: 2,
    role: "assistant",
    content: "The page introduces the GPU memory hierarchy.",
    provider: "deepseek",
    tier: "flash",
    created_at: "2026-11-13T08:00:04+00:00",
    reasoning: null,
    model: "deepseek-chat",
    thinking: "off",
    work_steps: [],
    citations: [],
    sources: [
      {
        marker: 1,
        kind: "course",
        title: "Lecture 1: GPU architecture",
        summary: "Registers, shared memory, and global memory sit at different levels.",
        doc_id: "ACS_Lecture_1_2026F",
        page_no: 7,
        url: null,
      },
    ],
    tool_calls: [],
  },
];

const SOURCE_FRAMES = [
  { type: "start", messageId: "answer-src" },
  { type: "text-start", id: "t1" },
  { type: "text-delta", id: "t1", delta: "This page maps the memory hierarchy." },
  { type: "text-end", id: "t1" },
  {
    type: "data-sources",
    data: {
      sources: [
        {
          marker: 1,
          kind: "course",
          title: "Lecture 1: GPU architecture",
          summary: "Registers, shared memory, and global memory sit at different levels.",
          doc_id: "ACS_Lecture_1_2026F",
          page_no: 7,
          url: null,
          chunk_id: "ACS_Lecture_1_2026F:p007:c00",
        },
      ],
    },
  },
  { type: "finish" },
  "[DONE]",
];

describe("document preview", () => {
  it("opens the file with a back arrow and page controls", async () => {
    stub = createFetchStub(routes());
    const router = renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=3&from=f-lectures");

    expect(await screen.findByRole("heading", { name: "ACS_Lecture_1_2026F.pdf" })).toBeInTheDocument();
    expect(await screen.findByText("3 / 67")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeEnabled();

    await userEvent.setup().click(screen.getByRole("button", { name: "Back to the knowledge base" }));

    expect(router.state.location.pathname).toBe("/knowledge");
    expect(router.state.location.search).toBe("?folder=f-lectures");
  });

  it("turns the page with the next control and the page input", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=3");

    await screen.findByText("3 / 67");

    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("4 / 67")).toBeInTheDocument();

    const input = screen.getByLabelText("Go to page");
    await user.clear(input);
    await user.type(input, "9");
    await user.click(screen.getByRole("button", { name: "Go" }));
    expect(await screen.findByText("9 / 67")).toBeInTheDocument();
  });

  it("keeps the page jump field empty until the reader types a page", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=3");

    await screen.findByText("3 / 67");
    const input = screen.getByLabelText("Go to page");
    expect(input).toHaveValue("");

    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("4 / 67")).toBeInTheDocument();
    expect(input).toHaveValue("");

    await user.type(input, "9");
    await user.click(screen.getByRole("button", { name: "Go" }));
    expect(await screen.findByText("9 / 67")).toBeInTheDocument();
    expect(input).toHaveValue("");
  });

  it("switches between single-page and continuous browsing", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=3");

    await screen.findByText("3 / 67");
    expect(screen.queryByTestId("pdf-scroll")).toBeNull();
    expect(screen.getByRole("button", { name: "Page view" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "Scroll view" }));

    expect(screen.getByTestId("pdf-scroll")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scroll view" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "Page view" }));

    expect(screen.queryByTestId("pdf-scroll")).toBeNull();
    expect(screen.getByRole("button", { name: "Page view" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("jumps to the requested page in continuous browsing", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();
    const scrollIntoView = vi.spyOn(Element.prototype, "scrollIntoView");
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=3");

    await screen.findByText("3 / 67");
    await user.click(screen.getByRole("button", { name: "Scroll view" }));
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalled());
    scrollIntoView.mockClear();

    const input = screen.getByLabelText("Go to page");
    await user.type(input, "9");
    await user.click(screen.getByRole("button", { name: "Go" }));

    expect(await screen.findByText("9 / 67")).toBeInTheDocument();
    await waitFor(() => {
      const targets = scrollIntoView.mock.instances
        .map((element) =>
          (element as Element).closest("[data-page]")?.getAttribute("data-page"),
        )
        .filter((target): target is string => target !== null);
      expect(targets).toContain("9");
    });
    scrollIntoView.mockRestore();
  });

  it("sends the open document and page with the next turn", async () => {
    const chat: StubRoute = {
      method: "POST",
      path: "/api/chat",
      handler: () =>
        sseResponse(STREAM_FRAMES, {
          headers: { "x-conversation-id": "conversation-1" },
        }),
    };
    stub = createFetchStub(routes([chat]));
    const user = userEvent.setup();
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=7");

    await screen.findByText("7 / 67");
    const pane = screen.getByTestId("document-chat-pane");
    expect(
      within(pane).getByText(/read the open page/i),
    ).toBeInTheDocument();

    await user.type(within(pane).getByLabelText("Your question"), "explain this page");
    await user.click(within(pane).getByRole("button", { name: "Send" }));

    await waitFor(() => {
      const post = stub?.calls.find((call) => call.method === "POST");
      expect(post?.body).toMatchObject({
        message: "explain this page",
        document_context: { doc_id: "ACS_Lecture_1_2026F", page_no: 7 },
      });
    });

    // The conversation id the backend assigns must not re-key the thread: the
    // answer stays visible after it arrives.
    expect(
      await within(pane).findByText(/GPU memory hierarchy/),
    ).toBeInTheDocument();
  });

  it("holds the answer's place in the pane while the reply is awaited", async () => {
    const answering = deferred();
    const chat: StubRoute = {
      method: "POST",
      path: "/api/chat",
      handler: async () => {
        await answering.promise;
        return sseResponse(STREAM_FRAMES, {
          headers: { "x-conversation-id": "conversation-1" },
        });
      },
    };
    stub = createFetchStub(routes([chat]));
    const user = userEvent.setup();
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=7");

    await screen.findByText("7 / 67");
    const pane = screen.getByTestId("document-chat-pane");
    await user.type(within(pane).getByLabelText("Your question"), "explain this page");
    await user.click(within(pane).getByRole("button", { name: "Send" }));

    // Nothing has streamed yet, so the pane shows the pending answer where the
    // answer will start instead of ending at the question.
    expect(
      await within(pane).findByText("Generating the answer"),
    ).toBeInTheDocument();
    expect(
      pane.querySelector('[data-slot="answer-pending"]'),
    ).not.toBeNull();

    answering.resolve();

    expect(
      await within(pane).findByText(/GPU memory hierarchy/),
    ).toBeInTheDocument();
    expect(pane.querySelector('[data-slot="answer-pending"]')).toBeNull();
  });
  it("loads this document's earlier conversation from the history button", async () => {
    window.localStorage.setItem(
      "vt.knowledge.chat.ACS_Lecture_1_2026F",
      "conversation-1",
    );
    const history: StubRoute = {
      method: "GET",
      path: "/api/sessions/conversation-1/messages",
      handler: () =>
        jsonResponse({ session_id: "conversation-1", messages: STORED_TURNS }),
    };
    stub = createFetchStub(routes([history]));
    const user = userEvent.setup();
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=7");

    await screen.findByText("7 / 67");
    const pane = screen.getByTestId("document-chat-pane");
    await user.click(
      within(pane).getByRole("button", {
        name: /earlier conversation for this file/i,
      }),
    );

    expect(
      await within(pane).findByText("What is on this page?"),
    ).toBeInTheDocument();
    expect(
      within(pane).getByText(/introduces the GPU memory hierarchy/),
    ).toBeInTheDocument();
    expect(
      within(pane).getByRole("button", { name: /Sources: 1 course page/i }),
    ).toHaveAttribute("aria-expanded", "false");
  });

  it("shows an answer's sources inline and expands them in place", async () => {
    const chat: StubRoute = {
      method: "POST",
      path: "/api/chat",
      handler: () =>
        sseResponse(SOURCE_FRAMES, {
          headers: { "x-conversation-id": "conversation-1" },
        }),
    };
    stub = createFetchStub(routes([chat]));
    const user = userEvent.setup();
    renderLiveRoute("/knowledge/docs/ACS_Lecture_1_2026F?page=7");

    await screen.findByText("7 / 67");
    const pane = screen.getByTestId("document-chat-pane");
    await user.type(within(pane).getByLabelText("Your question"), "explain this page");
    await user.click(within(pane).getByRole("button", { name: "Send" }));

    const disclosure = await within(pane).findByRole("button", {
      name: /Sources: 1 course page/i,
    });
    expect(disclosure).toHaveAttribute("aria-expanded", "false");
    expect(
      within(pane).queryByText("Lecture 1: GPU architecture"),
    ).not.toBeInTheDocument();

    await user.click(disclosure);

    expect(disclosure).toHaveAttribute("aria-expanded", "true");
    expect(
      within(pane).getByText("Lecture 1: GPU architecture"),
    ).toBeInTheDocument();
    expect(
      within(pane).getByRole("link", { name: /Lecture 1: GPU architecture/ }),
    ).toHaveAttribute("href", "/knowledge/docs/ACS_Lecture_1_2026F?page=7");
  });

  it("returns to the last document page from another view", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();
    const router = renderLiveRoute(
      "/knowledge/docs/ACS_Lecture_1_2026F?page=7&from=f-lectures",
    );

    await screen.findByText("7 / 67");

    await act(async () => {
      await router.navigate("/chat");
    });
    await user.click(screen.getByRole("link", { name: "Knowledge base" }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        "/knowledge/docs/ACS_Lecture_1_2026F",
      ),
    );
    expect(router.state.location.search).toBe("?page=7&from=f-lectures");
    expect(await screen.findByText("7 / 67")).toBeInTheDocument();

    // The same item returns to the library once the reader is already on a file.
    await user.click(screen.getByRole("link", { name: "Knowledge base" }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/knowledge"),
    );
  });

});
