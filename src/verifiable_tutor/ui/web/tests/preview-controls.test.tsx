import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  destinationAfterRoleSwitch,
  isAuthPath,
  safeNextPath,
} from "@/lib/auth/redirect";
import { renderRoute } from "./render-route";

async function choosePreviewRole(
  name: "Student" | "Instructor" | "Signed out",
): Promise<void> {
  const user = userEvent.setup();

  await user.click(screen.getByRole("button", { name: "Preview controls" }));
  await user.click(screen.getByRole("menuitemradio", { name }));
}

describe("preview role change on an authentication page", () => {
  it("returns a signed-out reviewer to the page they asked for", async () => {
    const router = renderRoute("/login?next=%2Fpractice", { role: "signed-out" });

    await choosePreviewRole("Student");

    expect(router.state.location.pathname).toBe("/practice");
  });

  it("returns to the chat page when the login page carries no next destination", async () => {
    const router = renderRoute("/login", { role: "signed-out" });

    await choosePreviewRole("Student");

    expect(router.state.location.pathname).toBe("/chat");
  });

  it("ignores an off-site next destination and stays inside the app", async () => {
    const router = renderRoute(
      `/login?next=${encodeURIComponent("https://evil.example/login")}`,
      { role: "signed-out" },
    );

    await choosePreviewRole("Student");

    expect(router.state.location.pathname).toBe("/chat");
  });

  it("keeps the authentication page open when the reviewer signs out", async () => {
    const router = renderRoute("/login", { role: "student" });

    await choosePreviewRole("Signed out");

    expect(router.state.location.pathname).toBe("/login");
  });

  it("enters the application when a signed-in student switches to instructor", async () => {
    const router = renderRoute("/login");

    await choosePreviewRole("Instructor");

    expect(router.state.location.pathname).toBe("/chat");
    expect(
      screen.getByRole("heading", { name: "Ask a course question" }),
    ).toBeInTheDocument();
  });

  it("sends a student who signs in on an instructor page to the chat page", async () => {
    const router = renderRoute("/login?next=%2Finstructor%2Fbuilds", {
      role: "signed-out",
    });

    await choosePreviewRole("Student");

    expect(router.state.location.pathname).toBe("/chat");
    expect(
      screen.queryByRole("heading", { name: "Instructor access required" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the instructor page when an instructor signs in from it", async () => {
    const router = renderRoute("/login?next=%2Finstructor%2Fbuilds", {
      role: "signed-out",
    });

    await choosePreviewRole("Instructor");

    expect(router.state.location.pathname).toBe("/instructor/builds");
    expect(
      screen.getByRole("heading", { name: "Knowledge-base builds" }),
    ).toBeInTheDocument();
  });

  it("does not return to an authentication page when next points at one", async () => {
    const router = renderRoute("/login?next=%2Flogin", { role: "signed-out" });

    await choosePreviewRole("Student");

    expect(router.state.location.pathname).toBe("/chat");
  });

  it("does not return to the registration page when next points at it", async () => {
    const router = renderRoute("/login?next=%2Fregister", {
      role: "signed-out",
    });

    await choosePreviewRole("Instructor");

    expect(router.state.location.pathname).toBe("/chat");
  });
});

describe("sanitized next destination", () => {
  it("keeps a same-origin path and its query as the destination", () => {
    expect(safeNextPath("/practice?tab=questions")).toBe("/practice?tab=questions");
  });

  it("falls back to the chat page for an off-site, relative, or malformed destination", () => {
    const rejected = [
      null,
      undefined,
      "",
      "   ",
      "practice",
      "https://evil.example/login",
      "//evil.example/login",
      "/\\evil.example",
      "javascript:alert(1)",
    ];

    for (const candidate of rejected) {
      expect(safeNextPath(candidate)).toBe("/chat");
    }
  });
});

describe("authentication page detection", () => {
  it("recognizes the five authentication routes", () => {
    for (const path of ["/login", "/register", "/verify", "/reset", "/reset/confirm"]) {
      expect(isAuthPath(path)).toBe(true);
    }
  });

  it("does not treat an application route as an authentication route", () => {
    for (const path of ["/chat", "/practice", "/reset/confirm/extra", "/"]) {
      expect(isAuthPath(path)).toBe(false);
    }
  });
});

describe("destination after a role switch", () => {
  it("keeps an instructor page for an instructor", () => {
    expect(destinationAfterRoleSwitch("/instructor/builds", "instructor")).toBe(
      "/instructor/builds",
    );
    expect(
      destinationAfterRoleSwitch("/instructor/deadlines?week=1", "instructor"),
    ).toBe("/instructor/deadlines?week=1");
  });

  it("sends a student away from an instructor-only page", () => {
    expect(destinationAfterRoleSwitch("/instructor/builds", "student")).toBe(
      "/chat",
    );
    expect(destinationAfterRoleSwitch("/instructor/deadlines", "student")).toBe(
      "/chat",
    );
  });

  it("always lands in the application, never on an authentication page", () => {
    for (const role of ["student", "instructor"] as const) {
      for (const path of [
        "/login",
        "/register",
        "/verify",
        "/reset",
        "/reset/confirm",
      ]) {
        expect(destinationAfterRoleSwitch(path, role)).toBe("/chat");
      }
    }
  });

  it("keeps an ordinary application page for either role", () => {
    expect(
      destinationAfterRoleSwitch("/practice?tab=questions", "student"),
    ).toBe("/practice?tab=questions");
    expect(destinationAfterRoleSwitch("/knowledge", "instructor")).toBe(
      "/knowledge",
    );
    expect(destinationAfterRoleSwitch(null, "instructor")).toBe("/chat");
  });
});
