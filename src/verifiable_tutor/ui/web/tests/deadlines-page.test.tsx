import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderRoute } from "./render-route";

describe("deadlines page", () => {
  it("renders the registry version, the clock, and the five policy states", () => {
    renderRoute("/instructor/deadlines", { role: "instructor" });

    expect(
      screen.getByRole("heading", { name: "Deadline registry" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/deadlines-2026-11-01/)).toBeInTheDocument();
    expect(
      screen.getByText(/Assignment 2: CUDA attention/),
    ).toBeInTheDocument();
    expect(screen.getByText("Not released")).toBeInTheDocument();
    expect(screen.getByText("Extension")).toBeInTheDocument();
    expect(screen.getByText("After the deadline")).toBeInTheDocument();
  });

  it("shows the fail-closed notice when a state is unknown", () => {
    renderRoute("/instructor/deadlines", { role: "instructor" });

    expect(
      screen.getByText("An unknown assignment blocks disclosure"),
    ).toBeInTheDocument();
    expect(screen.getByText("Not in the registry")).toBeInTheDocument();
  });

  it("marks the view as read-only", () => {
    renderRoute("/instructor/deadlines", { role: "instructor" });

    expect(
      screen.getByText("Read-only. Editing the registry is not available yet."),
    ).toBeInTheDocument();
  });

  it("shows the empty state", () => {
    renderRoute("/instructor/deadlines", {
      role: "instructor",
      pageState: "empty",
    });

    expect(screen.getByText("The registry is empty")).toBeInTheDocument();
  });
});
