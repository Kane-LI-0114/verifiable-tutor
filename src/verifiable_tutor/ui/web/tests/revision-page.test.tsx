import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { createFetchStub, jsonResponse, type StubRoute } from "./api-stub";
import { renderLiveRoute } from "./render-live-route";

const STUDENT = { id: "u1", email: "student@ust.hk", role: "student" };

const TREE = {
  themes: [
    {
      id: "t1",
      title: "Memory and attention",
      summary: "How data movement shapes attention.",
      position: 0,
      documents: [
        {
          doc_id: "ACS_lecture_2_2026F",
          title: "Memory hierarchy",
          filename: "ACS_lecture_2_2026F.pdf",
          category: "lecture",
        },
        {
          doc_id: "Tutorial_4",
          title: "Tutorial 4: FlashAttention",
          filename: "Tutorial_4.pdf",
          category: "tutorial",
        },
      ],
    },
    {
      id: "t2",
      title: "Engineering practice",
      summary: "The course project and its platform.",
      position: 1,
      documents: [
        {
          doc_id: "Assignment_2",
          title: "Assignment 2",
          filename: "Assignment_2.pdf",
          category: "assignment",
        },
      ],
    },
  ],
};

let stub: ReturnType<typeof createFetchStub> | null = null;

function routes(tree: unknown = TREE): StubRoute[] {
  return [
    { method: "GET", path: "/api/auth/me", handler: () => jsonResponse(STUDENT) },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse({ sessions: [] }),
    },
    { method: "GET", path: "/api/revision", handler: () => jsonResponse(tree) },
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
    expect(screen.getAllByText("Not generated")).toHaveLength(3);
    expect(
      screen.queryByRole("link", { name: /Tutorial 4: FlashAttention/ }),
    ).not.toBeInTheDocument();
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

  it("shows the empty state before the outline is built", async () => {
    stub = createFetchStub(routes({ themes: [] }));
    renderLiveRoute("/revision");

    expect(await screen.findByText("No revision guide yet")).toBeInTheDocument();
  });
});
