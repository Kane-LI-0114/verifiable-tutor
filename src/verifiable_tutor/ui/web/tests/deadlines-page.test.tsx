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
    expect(screen.getByText("Pre-release")).toBeInTheDocument();
    expect(screen.getByText("Extension window")).toBeInTheDocument();
    expect(screen.getByText("Post-deadline")).toBeInTheDocument();
  });

  it("shows the fail-closed notice when a state is unknown", () => {
    renderRoute("/instructor/deadlines", { role: "instructor" });

    expect(
      screen.getByText("Unknown state fails closed"),
    ).toBeInTheDocument();
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });

  it("marks the view as read-only", () => {
    renderRoute("/instructor/deadlines", { role: "instructor" });

    expect(
      screen.getByText("Read-only view. The in-app editor is a P1 item."),
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
