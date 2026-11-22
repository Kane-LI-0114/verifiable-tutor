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

function tileIds(): (string | null)[] {
  return screen
    .getAllByTestId(/^file-tile-/)
    .map((tile) => tile.getAttribute("data-testid"));
}

function routes(overrides: StubRoute[] = []): StubRoute[] {
  return [
    // Overrides come first so a test can replace a default route.
    ...overrides,
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
    expect(screen.getByRole("button", { name: "Sort" })).toBeInTheDocument();
    expect(screen.queryByText("2 files")).not.toBeInTheDocument();
    const image = screen
      .getByTestId("file-tile-ACS_Lecture_1_2026F")
      .querySelector("img");
    expect(image?.getAttribute("src")).toBe(
      "/api/corpus/ACS_Lecture_1_2026F/pages/1.webp",
    );
  });

  it("sorts files by created time ascending by default and selects that menu item", async () => {
    const older = { ...DOC_A, created_at: "2026-10-01T00:00:00+00:00" };
    const newer = { ...DOC_B, created_at: "2026-11-01T00:00:00+00:00" };
    const newestFirst: StubRoute = {
      method: "GET",
      path: "/api/knowledge/documents",
      handler: () => jsonResponse({ documents: [newer, older], total: 2 }),
    };
    stub = createFetchStub(routes([newestFirst]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-Tutorial_2");

    expect(tileIds()).toEqual([
      "file-tile-ACS_Lecture_1_2026F",
      "file-tile-Tutorial_2",
    ]);

    await user.click(screen.getByRole("button", { name: "Sort" }));
    const created = screen.getByRole("menuitem", { name: "Sort by created time" });
    const name = screen.getByRole("menuitem", { name: "Sort by name" });
    expect(created).toHaveAttribute("title", "Ascending");
    expect(name).not.toHaveAttribute("title");
    expect(created.querySelectorAll("svg").length).toBeGreaterThan(0);
    expect(name.querySelectorAll("svg")).toHaveLength(0);
  });

  it("falls back to created time ascending when the stored sort is invalid", async () => {
    window.localStorage.setItem("vt.knowledge.sort", "created:sideways");
    const older = { ...DOC_A, created_at: "2026-10-01T00:00:00+00:00" };
    const newer = { ...DOC_B, created_at: "2026-11-01T00:00:00+00:00" };
    const newestFirst: StubRoute = {
      method: "GET",
      path: "/api/knowledge/documents",
      handler: () => jsonResponse({ documents: [newer, older], total: 2 }),
    };
    stub = createFetchStub(routes([newestFirst]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-Tutorial_2");

    expect(tileIds()).toEqual([
      "file-tile-ACS_Lecture_1_2026F",
      "file-tile-Tutorial_2",
    ]);

    await user.click(screen.getByRole("button", { name: "Sort" }));
    expect(
      screen.getByRole("menuitem", { name: "Sort by created time" }),
    ).toHaveAttribute("title", "Ascending");
  });

  it("restores the sort key and direction from browser storage on the next visit", async () => {
    const older = { ...DOC_A, created_at: "2026-10-01T00:00:00+00:00" };
    const newer = { ...DOC_B, created_at: "2026-11-01T00:00:00+00:00" };
    const newestFirst: StubRoute = {
      method: "GET",
      path: "/api/knowledge/documents",
      handler: () => jsonResponse({ documents: [newer, older], total: 2 }),
    };
    stub = createFetchStub(routes([newestFirst]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-Tutorial_2");

    await user.click(screen.getByRole("button", { name: "Sort" }));
    await user.click(screen.getByRole("menuitem", { name: "Sort by name" }));
    await user.click(screen.getByRole("button", { name: "Sort" }));
    await user.click(screen.getByRole("menuitem", { name: "Sort by name" }));
    await waitFor(() => {
      expect(tileIds()).toEqual([
        "file-tile-Tutorial_2",
        "file-tile-ACS_Lecture_1_2026F",
      ]);
    });
    expect(window.localStorage.getItem("vt.knowledge.sort")).toBe("name:desc");

    cleanup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-Tutorial_2");
    expect(tileIds()).toEqual([
      "file-tile-Tutorial_2",
      "file-tile-ACS_Lecture_1_2026F",
    ]);
    await user.click(screen.getByRole("button", { name: "Sort" }));
    expect(
      screen.getByRole("menuitem", { name: "Sort by name" }),
    ).toHaveAttribute("title", "Descending");
    expect(
      screen.getByRole("menuitem", { name: "Sort by created time" }),
    ).not.toHaveAttribute("title");
  });

  it("sorts the file tiles by name after choosing the name sort item", async () => {
    const unsorted: StubRoute = {
      method: "GET",
      path: "/api/knowledge/documents",
      handler: () => jsonResponse({ documents: [DOC_B, DOC_A], total: 2 }),
    };
    stub = createFetchStub(routes([unsorted]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-Tutorial_2");

    expect(tileIds()).toEqual([
      "file-tile-Tutorial_2",
      "file-tile-ACS_Lecture_1_2026F",
    ]);

    await user.click(screen.getByRole("button", { name: "Sort" }));
    expect(screen.getAllByRole("menuitem")).toHaveLength(2);
    await user.click(screen.getByRole("menuitem", { name: "Sort by name" }));

    await waitFor(() => {
      expect(tileIds()).toEqual([
        "file-tile-ACS_Lecture_1_2026F",
        "file-tile-Tutorial_2",
      ]);
    });
  });

  it("keeps the sort menu as wide as its longest label", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    await user.click(screen.getByRole("button", { name: "Sort" }));

    const menu = document.querySelector('[data-slot="dropdown-menu-content"]');
    expect(menu).toHaveClass("w-max", "whitespace-nowrap");
    expect(menu).not.toHaveClass("w-(--radix-dropdown-menu-trigger-width)");
  });

  it("toggles the name direction when the same sort item is clicked twice", async () => {
    const unsorted: StubRoute = {
      method: "GET",
      path: "/api/knowledge/documents",
      handler: () => jsonResponse({ documents: [DOC_B, DOC_A], total: 2 }),
    };
    stub = createFetchStub(routes([unsorted]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-Tutorial_2");

    await user.click(screen.getByRole("button", { name: "Sort" }));
    await user.click(screen.getByRole("menuitem", { name: "Sort by name" }));
    await waitFor(() => {
      expect(tileIds()).toEqual([
        "file-tile-ACS_Lecture_1_2026F",
        "file-tile-Tutorial_2",
      ]);
    });

    await user.click(screen.getByRole("button", { name: "Sort" }));
    await user.click(screen.getByRole("menuitem", { name: "Sort by name" }));
    await waitFor(() => {
      expect(tileIds()).toEqual([
        "file-tile-Tutorial_2",
        "file-tile-ACS_Lecture_1_2026F",
      ]);
    });
  });

  it("sorts by created time and toggles newest and oldest on a second click", async () => {
    const older = { ...DOC_A, created_at: "2026-10-01T00:00:00+00:00" };
    const newer = { ...DOC_B, created_at: "2026-11-01T00:00:00+00:00" };
    const serverOrder: StubRoute = {
      method: "GET",
      path: "/api/knowledge/documents",
      handler: () => jsonResponse({ documents: [older, newer], total: 2 }),
    };
    stub = createFetchStub(routes([serverOrder]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-Tutorial_2");

    expect(tileIds()).toEqual([
      "file-tile-ACS_Lecture_1_2026F",
      "file-tile-Tutorial_2",
    ]);

    await user.click(screen.getByRole("button", { name: "Sort" }));
    await user.click(screen.getByRole("menuitem", { name: "Sort by created time" }));
    await waitFor(() => {
      expect(tileIds()).toEqual([
        "file-tile-Tutorial_2",
        "file-tile-ACS_Lecture_1_2026F",
      ]);
    });

    await user.click(screen.getByRole("button", { name: "Sort" }));
    await user.click(screen.getByRole("menuitem", { name: "Sort by created time" }));
    await waitFor(() => {
      expect(tileIds()).toEqual([
        "file-tile-ACS_Lecture_1_2026F",
        "file-tile-Tutorial_2",
      ]);
    });
  });

  it("offers the folder delete action to a student", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    await user.click(screen.getByRole("button", { name: "Folder actions" }));

    expect(
      screen.getByRole("menuitem", { name: "Move folder" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "Delete folder" }),
    ).not.toHaveAttribute("aria-disabled", "true");
    expect(
      screen.queryByText("Only instructors can delete folders"),
    ).not.toBeInTheDocument();
  });

  it("lets an instructor use the folder delete action", async () => {
    const instructor: StubRoute = {
      method: "GET",
      path: "/api/auth/me",
      handler: () => jsonResponse({ ...STUDENT, role: "instructor" }),
    };
    stub = createFetchStub(routes([instructor]));
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    await user.click(screen.getByRole("button", { name: "Folder actions" }));
    expect(
      screen.getByRole("menuitem", { name: "Delete folder" }),
    ).not.toHaveAttribute("aria-disabled", "true");
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
    expect(within(pane).getByText("Summary by qwen3.8-27b")).toBeInTheDocument();
    expect(within(pane).getByText("67")).toBeInTheDocument();
  });

  it("keeps the name and the metadata band while only the summary scrolls", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    const tile = await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");
    await user.click(within(tile).getByText("ACS_Lecture_1_2026F"));

    const header = screen.getByTestId("file-info-header");
    const scroll = screen.getByTestId("file-info-scroll");
    const footer = screen.getByTestId("file-info-footer");

    expect(within(header).getByRole("heading", { name: "ACS_Lecture_1_2026F" })).toBeInTheDocument();
    expect(
      within(scroll).getByText("A lecture on GPU architecture and CUDA execution."),
    ).toBeInTheDocument();
    expect(within(scroll).queryByRole("button", { name: "Ask about this file" })).toBeNull();
    expect(
      within(footer).getByRole("button", { name: "Ask about this file" }),
    ).toBeInTheDocument();
    expect(within(footer).getByText("Created")).toBeInTheDocument();
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
    expect(
      screen.queryByRole("menuitem", { name: "Upload file" }),
    ).not.toBeInTheDocument();

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

  it("offers the file delete action to a student", async () => {
    stub = createFetchStub(routes());
    const user = userEvent.setup();

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    const tile = screen.getByTestId("file-tile-ACS_Lecture_1_2026F");
    await user.click(within(tile).getByRole("button", { name: "File actions" }));

    expect(
      screen.getByRole("menuitem", { name: "Delete file" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "Move file" }),
    ).toBeInTheDocument();
  });

  it("renders file and folder tiles with a locked 4:3 landscape face", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/knowledge");

    const fileTile = await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");
    expect(fileTile).toHaveClass("aspect-[4/3]");

    const folderTile = screen.getByTestId("folder-tile-f-lectures");
    expect(folderTile).toHaveClass("aspect-[4/3]");
  });

  it("keeps fixed-size tile tracks so pane toggles never stretch the cards", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    const grid = screen.getByTestId("knowledge-grid");
    // A standard card grid: every track keeps the same fixed size and
    // as many columns as fit wrap onto each row. The card size never
    // depends on the animated pane widths, so a sidebar toggle can only
    // change how many columns fit, never how big the cards are. Nine rem
    // is the track size that keeps the leftover width small on the usual
    // split views, so the row gaps do not have to grow much.
    expect(grid.className).toContain("grid-cols-[repeat(auto-fill,9rem)]");
    expect(grid.className).not.toContain("1fr");
    expect(grid.className).not.toContain("minmax");
  });

  it("spreads the tile row across the pane so no dead column sits on the right", async () => {
    stub = createFetchStub(routes());

    renderLiveRoute("/knowledge");
    await screen.findByTestId("file-tile-ACS_Lecture_1_2026F");

    const grid = screen.getByTestId("knowledge-grid");
    // The tracks keep the card size fixed. Whatever width is left after
    // the columns do not fit again goes into the gaps, so a row reaches
    // both edges of the pane instead of trailing dead space.
    expect(grid).toHaveClass("justify-between");
  });
});
