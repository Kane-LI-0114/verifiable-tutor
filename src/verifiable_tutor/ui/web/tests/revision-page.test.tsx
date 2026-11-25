import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { createFetchStub, jsonResponse, type StubRoute } from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const STUDENT = { id: "u1", email: "student@ust.hk", role: "student" };

function document(overrides: Record<string, unknown> = {}) {
  return {
    doc_id: "Tutorial_4",
    title: "Tutorial 4: FlashAttention",
    filename: "Tutorial_4.pdf",
    category: "tutorial",
    generated: false,
    total: 0,
    mastered: 0,
    ...overrides,
  };
}

const TREE = {
  total: 2,
  mastered: 0,
  themes: [
    {
      id: "t1",
      title: "Memory and attention",
      summary: "How data movement shapes attention.",
      position: 0,
      total: 2,
      mastered: 0,
      documents: [
        document({
          doc_id: "ACS_lecture_2_2026F",
          title: "Memory hierarchy",
          filename: "ACS_lecture_2_2026F.pdf",
          category: "lecture",
        }),
        document({ generated: true, total: 2, mastered: 0 }),
      ],
    },
    {
      id: "t2",
      title: "Engineering practice",
      summary: "The course project and its platform.",
      position: 1,
      total: 0,
      mastered: 0,
      documents: [
        document({
          doc_id: "Assignment_2",
          title: "Assignment 2",
          filename: "Assignment_2.pdf",
          category: "assignment",
        }),
      ],
    },
  ],
};

const DETAIL = {
  doc_id: "Tutorial_4",
  title: "Tutorial 4: FlashAttention",
  filename: "Tutorial_4.pdf",
  category: "tutorial",
  theme_id: "t1",
  theme_title: "Memory and attention",
  intro_markdown: "A short overview of the chapter.",
  model: "deepseek-flash",
  generated_at: "2026-11-25T09:00:00+00:00",
  total: 2,
  mastered: 0,
  points: [
    {
      id: "p1",
      title: "Online softmax",
      body_markdown: "Online softmax keeps a running maximum.",
      position: 0,
      page_no: 23,
      mastered: false,
    },
    {
      id: "p2",
      title: "Bank conflicts",
      body_markdown: "Shared memory is split into banks.",
      position: 1,
      page_no: 12,
      mastered: false,
    },
  ],
};

let stub: ReturnType<typeof createFetchStub> | null = null;

function routes(tree: unknown = TREE, extra: StubRoute[] = []): StubRoute[] {
  return [
    { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse({ sessions: [] }),
    },
    { method: "GET", path: "/api/revision", handler: () => jsonResponse(tree) },
    ...extra,
  ];
}

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("revision guide", () => {
  it("lists themes and their documents with a category colour", async () => {
    stub = createFetchStub(routes());
    renderLiveRoute("/revision");

    expect(await screen.findByText("Memory and attention")).toBeInTheDocument();
    expect(screen.getByText("Engineering practice")).toBeInTheDocument();
    expect(
      screen.getByText("How data movement shapes attention."),
    ).toBeInTheDocument();
    expect(screen.getByText("Memory hierarchy")).toBeInTheDocument();
    expect(screen.getByText("Tutorial 4: FlashAttention")).toBeInTheDocument();
    expect(screen.getByText("Lecture")).toBeInTheDocument();
    expect(screen.getByText("Tutorial")).toBeInTheDocument();
    expect(screen.getByText("Assignment")).toBeInTheDocument();
    expect(screen.getByText("Course progress")).toBeInTheDocument();
  });

  it("collapses and expands a theme", async () => {
    const user = userEvent.setup();
    stub = createFetchStub(routes());
    renderLiveRoute("/revision");

    const header = await screen.findByRole("button", {
      name: /Memory and attention/,
    });
    await user.click(header);

    await waitFor(() =>
      expect(screen.queryByText("Memory hierarchy")).not.toBeInTheDocument(),
    );

    await user.click(header);

    expect(await screen.findByText("Memory hierarchy")).toBeInTheDocument();
  });

  it("opens a generated document and marks points known", async () => {
    const user = userEvent.setup();
    stub = createFetchStub(
      routes(TREE, [
        {
          method: "GET",
          path: "/api/revision/docs/Tutorial_4",
          handler: () => jsonResponse(DETAIL),
        },
        {
          method: "PATCH",
          path: "/api/revision/points/p1",
          handler: () =>
            jsonResponse({ doc_id: "Tutorial_4", total: 2, mastered: 1 }),
        },
      ]),
    );
    renderLiveRoute("/revision");

    await user.click(
      await screen.findByRole("link", { name: /Tutorial 4: FlashAttention/ }),
    );

    expect(await screen.findByText("A short overview of the chapter.")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Online softmax" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download .md" })).toHaveAttribute(
      "href",
      "/api/revision/docs/Tutorial_4/markdown",
    );
    expect(screen.getByRole("link", { name: "Open page 23" })).toHaveAttribute(
      "href",
      "/knowledge/docs/Tutorial_4?page=23",
    );

    await user.click(screen.getByRole("checkbox", { name: "Online softmax" }));

    await waitFor(() =>
      expect(screen.getByRole("checkbox", { name: "Online softmax" })).toBeChecked(),
    );
  });

  it("shows the empty state before the outline is built", async () => {
    stub = createFetchStub(routes({ themes: [], total: 0, mastered: 0 }));
    renderLiveRoute("/revision");

    expect(await screen.findByText("No revision guide yet")).toBeInTheDocument();
  });
});
