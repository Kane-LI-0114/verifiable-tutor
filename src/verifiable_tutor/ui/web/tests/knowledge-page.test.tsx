import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createFetchStub, jsonResponse, type StubRoute } from "./api-stub";
import { installMemoryStorage } from "./memory-storage";
import { renderLiveRoute } from "./render-live-route";

const STUDENT = {
  id: "u-student",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-11-02T12:00:00+00:00",
};

const DOC_A = {
  id: "ACS_Lecture_1_2026F",
  title: "ACS_Lecture_1_2026F",
  filename: "ACS_Lecture_1_2026F.pdf",
  folder_id: null,
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
const DOC_B = {
  ...DOC_A,
  id: "Tutorial_2",
  title: "Tutorial_2",
  filename: "Tutorial_2.pdf",
  page_count: 25,
  chunk_count: 27,
  status: "processing",
  summary: null,
  summary_model: null,
  pdf_url: "/api/knowledge/documents/Tutorial_2/file",
  thumbnail_url: "/api/corpus/Tutorial_2/pages/1.webp",
};
const FOLDER = {
  id: "f-lectures",
  name: "Lectures",
  parent_id: null,
  position: 0,
  created_at: "2026-11-05T04:00:00+00:00",
  file_count: 1,
  path: [{ id: "f-lectures", name: "Lectures" }],
};

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
      path: "/api/knowledge/folders",
      handler: () => jsonResponse({ folders: [FOLDER], total_files: 2 }),
    },
    {
      method: "GET",
      path: "/api/knowledge/documents",
      handler: () => jsonResponse({ documents: [DOC_A, DOC_B], total: 2 }),
    },
    {
      method: "GET",
      path: "/api/knowledge/cards",
      handler: () => jsonResponse({ cards: [], total: 0 }),
    },
    ...overrides,
  ];
}

beforeEach(() => {
  installMemoryStorage();
});

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("knowledge browser", () => {
  it("lists folders and files with their real first page as the icon", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/knowledge");

    expect(
      await screen.findByTestId("file-tile-ACS_Lecture_1_2026F"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Knowledge base" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Lectures")).toBeInTheDocument();
    expect(screen.getByText("2 files")).toBeInTheDocument();
    const image = screen
      .getByTestId("file-tile-ACS_Lecture_1_2026F")
      .querySelector("img");
    expect(image?.getAttribute("src")).toBe(
      "/api/corpus/ACS_Lecture_1_2026F/pages/1.webp",
    );
  });

  it("marks the indexing state of a file that is still being processed", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/knowledge");

    const tile = await screen.findByTestId("file-tile-Tutorial_2");
    expect(within(tile).getByText("Indexing")).toBeInTheDocument();
  });

  it("shows the file record in the right pane when a tile is selected", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");

    const tile = await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");
    await user.click(within(tile).getByText("ACS_Lecture_1_2026F"));

    const pane = screen.getByTestId("knowledge-pane");
    expect(
      within(pane).getByText("A lecture on GPU architecture and CUDA execution."),
    ).toBeInTheDocument();
    expect(within(pane).getByText("Written by qwen3.8-27b")).toBeInTheDocument();
    expect(within(pane).getByText("67")).toBeInTheDocument();
  });

  it("keeps upload disabled and creates a folder from the new menu", async () => {
    const created: StubRoute = {
      method: "POST",
      path: "/api/knowledge/folders",
      handler: () =>
        jsonResponse(
          { ...FOLDER, id: "f-new", name: "Week 1", path: [] },
          { status: 201 },
        ),
    };
    stub = createFetchStub(routes([created]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    await user.click(screen.getByRole("button", { name: "New" }));
    const upload = screen.getByRole("menuitem", { name: "Upload file" });
    expect(upload).toHaveAttribute("aria-disabled", "true");

    await user.click(screen.getByRole("menuitem", { name: "New folder" }));
    await user.type(screen.getByLabelText("Folder name"), "Week 1");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      const post = stub?.calls.find((call) => call.method === "POST");
      expect(post?.body).toEqual({ name: "Week 1", parent_id: null });
    });
  });

  it("shows why a document matched and marks the words", async () => {
    const search: StubRoute = {
      method: "GET",
      path: "/api/knowledge/search",
      handler: () =>
        jsonResponse({
          query: "allreduce",
          documents: [
            {
              ...DOC_A,
              matches: [
                {
                  kind: "content",
                  page_no: 12,
                  snippet: "The allreduce operation combines gradients.",
                  highlights: [[4, 13]],
                },
              ],
            },
          ],
        }),
    };
    stub = createFetchStub(routes([search]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    await user.type(
      screen.getByLabelText("Search the knowledge base"),
      "allreduce",
    );

    expect(await screen.findByText("page 12")).toBeInTheDocument();
    expect(screen.getByText("allreduce", { selector: "mark" })).toBeInTheDocument();
  });

  it("remembers the collapsed file pane across a reload", async () => {
    stub = createFetchStub(routes());
    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");
    await userEvent.setup().click(screen.getByRole("button", { name: "Collapse the panel" }));
    expect(screen.getByTestId("knowledge-pane")).toHaveAttribute("data-collapsed", "true");

    cleanup();

    renderLiveRoute("/knowledge");
    expect(
      await screen.findByRole("complementary", { name: "Selected file" }),
    ).toHaveAttribute("data-collapsed", "true");
  });

  it("offers the delete action only to an instructor", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    const tile = screen.getByTestId("file-tile-ACS_Lecture_1_2026F");
    await user.click(within(tile).getByRole("button", { name: "File actions" }));

    expect(
      screen.queryByRole("menuitem", { name: "Delete file" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "Move file" }),
    ).toBeInTheDocument();
  });
});
