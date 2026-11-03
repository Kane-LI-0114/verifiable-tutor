import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";

import { routes } from "@/app/routes";
import { Providers } from "@/app/providers";
import type { PreviewRole } from "@/lib/preview/session";
import { previewSession } from "@/lib/preview/session";

function renderAt(path: string, role: PreviewRole) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });

  render(
    <Providers session={previewSession(role)}>
      <RouterProvider router={router} />
    </Providers>,
  );
}

describe("routes and guards", () => {
  it("sends a signed-in visitor from the root to a new conversation", () => {
    renderAt("/", "student");

    expect(
      screen.getByRole("heading", { name: "Ask a course question" }),
    ).toBeInTheDocument();
  });

  it("sends an anonymous visitor to the login page", () => {
    renderAt("/chat", "signed-out");

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("blocks a student from an instructor route", () => {
    renderAt("/instructor/builds", "student");

    expect(
      screen.getByRole("heading", { name: "Instructor access required" }),
    ).toBeInTheDocument();
  });

  it("lets an instructor open the build console", () => {
    renderAt("/instructor/builds", "instructor");

    expect(
      screen.getByRole("heading", { name: "Knowledge-base builds" }),
    ).toBeInTheDocument();
  });

  it("hides the instructor navigation from a student", () => {
    renderAt("/chat", "student");

    expect(screen.queryByRole("link", { name: "Builds" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Deadlines" })).not.toBeInTheDocument();
  });

  it("shows the instructor navigation to an instructor", () => {
    renderAt("/chat", "instructor");

    expect(screen.getByRole("link", { name: "Builds" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Deadlines" })).toBeInTheDocument();
  });

  it("keeps the preview and language controls on the not-found page", () => {
    renderAt("/no-such-page", "student");

    expect(
      screen.getByRole("button", { name: "Preview controls" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "中文" })).toBeInTheDocument();
  });

  it("renders the not-found page for an unknown path", () => {
    renderAt("/no-such-page", "student");

    expect(
      screen.getByRole("heading", { name: "Page not found" }),
    ).toBeInTheDocument();
  });
});
