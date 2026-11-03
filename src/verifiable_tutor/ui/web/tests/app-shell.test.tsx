import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { renderRoute } from "./render-route";

describe("app shell", () => {
  beforeEach(() => {
    document.cookie = "sidebar_state=; path=/; max-age=0";
    document.title = "Verifiable Tutor";
  });

  it("keeps the redundant chat tab out of the primary navigation", () => {
    renderRoute("/chat");

    expect(screen.queryByRole("link", { name: "Chat" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New question" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Practice" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Knowledge base" })).toBeInTheDocument();
  });

  it("moves the account menu and sign out to the sidebar footer", async () => {
    const user = userEvent.setup();
    const router = renderRoute("/chat");

    await user.click(screen.getByRole("button", { name: "student@ust.hk" }));
    await user.click(screen.getByRole("menuitem", { name: "Sign out" }));

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
    expect(router.state.location.search).toContain("next=%2Fchat");
  });

  it("does not repeat the account control in the top bar", () => {
    renderRoute("/chat");

    const header = screen.getByRole("banner");

    expect(
      within(header).queryByRole("button", { name: "student@ust.hk" }),
    ).not.toBeInTheDocument();
    expect(
      within(header).getByRole("button", { name: "Preview controls" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: "student@ust.hk" }),
    ).toHaveLength(1);
  });

  it("names the document after the current page", async () => {
    const router = renderRoute("/chat");

    expect(document.title).toContain("Chat");

    await act(async () => {
      await router.navigate("/practice");
    });

    await waitFor(() => expect(document.title).toContain("Practice"));
  });

  it("moves focus to the main region after a navigation", async () => {
    const router = renderRoute("/chat");

    await act(async () => {
      await router.navigate("/practice");
    });

    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole("main")),
    );
  });

  it("collapses the sidebar to the logo only and restores the name", async () => {
    const user = userEvent.setup();
    renderRoute("/chat");

    expect(screen.getByText("CSIT6000V")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open navigation" }));

    expect(screen.queryByText("CSIT6000V")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Verifiable Tutor" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "student@ust.hk" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open navigation" }));

    expect(screen.getByText("CSIT6000V")).toBeInTheDocument();
  });

  it("restores the collapsed sidebar after a reload", () => {
    document.cookie = "sidebar_state=false; path=/";

    renderRoute("/chat");

    expect(screen.queryByText("CSIT6000V")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Verifiable Tutor" }),
    ).toBeInTheDocument();
  });

  it("closes the navigation sheet after a mobile navigation", async () => {
    const originalMatchMedia = window.matchMedia;
    const originalInnerWidth = window.innerWidth;
    window.matchMedia = ((query: string) => ({
      matches: query.includes("767"),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    try {
      const user = userEvent.setup();
      const router = renderRoute("/chat");

      await user.click(screen.getByRole("button", { name: "Open navigation" }));
      const sheet = await screen.findByRole("dialog");
      await user.click(within(sheet).getByRole("link", { name: "Practice" }));

      expect(router.state.location.pathname).toBe("/practice");
      await waitFor(() =>
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
      );
    } finally {
      window.matchMedia = originalMatchMedia;
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        value: originalInnerWidth,
      });
    }
  });
});
