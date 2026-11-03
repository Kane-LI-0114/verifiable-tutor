import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderRoute } from "./render-route";

describe("knowledge page", () => {
  it("renders the card grid, the search controls, and the card count", () => {
    renderRoute("/knowledge");

    expect(
      screen.getByRole("heading", { name: "Knowledge base" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Search cards")).toBeInTheDocument();
    expect(screen.getByText("3 cards")).toBeInTheDocument();
    expect(
      screen.getByText(/This page introduces the course project/),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open the card" })).toHaveLength(3);
  });

  it("filters cards by the search text", async () => {
    const user = userEvent.setup();
    renderRoute("/knowledge");

    await user.type(screen.getByLabelText("Search cards"), "MPI_Allreduce");

    expect(screen.getByText("1 cards")).toBeInTheDocument();
    expect(
      screen.queryByText(/This page introduces the course project/),
    ).not.toBeInTheDocument();
  });

  it("opens a card with its study questions and citations", async () => {
    const user = userEvent.setup();
    renderRoute("/knowledge");

    await user.click(screen.getAllByRole("button", { name: "Open the card" })[0]);

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getAllByText("Course Project").length).toBeGreaterThan(0);
    expect(
      within(dialog).getByText("What is the primary objective of the course project?"),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByRole("button", { name: "Use in a review outline" }),
    ).toBeInTheDocument();
  });

  it("shows the empty state when no card matches", async () => {
    const user = userEvent.setup();
    renderRoute("/knowledge");

    await user.type(screen.getByLabelText("Search cards"), "no-such-term");

    expect(screen.getByText("No cards match")).toBeInTheDocument();
  });

  it("shows the loading state", () => {
    renderRoute("/knowledge", { pageState: "loading" });

    expect(screen.getByRole("status", { name: "Loading cards" })).toBeInTheDocument();
  });
});
