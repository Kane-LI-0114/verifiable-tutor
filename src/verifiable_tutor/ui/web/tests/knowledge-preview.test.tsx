import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createFetchStub, jsonResponse, sseResponse, type StubRoute } from "./api-stub";
import { installMemoryStorage } from "./memory-storage";
import { renderLiveRoute } from "./render-live-route";

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
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
  })) as never;
});

afterEach(() => {
  stub?.restore();
  stub = null;
});

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
      within(pane).getByText(/content is not/i),
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
  });
});
