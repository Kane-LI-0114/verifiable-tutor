import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderRoute } from "./render-route";

describe("knowledge-base builds page", () => {
  it("formats the build timestamps instead of printing raw ISO strings", () => {
    renderRoute("/instructor/builds", { role: "instructor" });

    expect(screen.queryByText("2026-11-02T11:58:00+00:00")).not.toBeInTheDocument();
    expect(screen.queryByText("2026-11-03T10:44:00+00:00")).not.toBeInTheDocument();
    expect(screen.getAllByText(/Nov 2026/).length).toBeGreaterThan(0);
  });

  it("describes a build by its document and job instead of repeating the state", async () => {
    const user = userEvent.setup();
    renderRoute("/instructor/builds", { role: "instructor" });

    await user.click(screen.getByRole("button", { name: /kb-20261103-03/ }));

    const list = screen.getByLabelText("Knowledge-base builds");
    expect(within(list).getAllByText(/Document id: /).length).toBe(4);
    // The queued row shows its state once, as the badge, not a second time as
    // the description.
    expect(within(list).getAllByText("Queued")).toHaveLength(1);
  });

  it("offers a retry action on a failed build", async () => {
    const user = userEvent.setup();
    renderRoute("/instructor/builds", { role: "instructor" });

    await user.click(screen.getByRole("button", { name: /kb-20261101-04/ }));

    expect(
      screen.getByRole("button", { name: "Retry the build" }),
    ).toBeDisabled();
  });

  it("describes the new-build action in its dialog", async () => {
    const user = userEvent.setup();
    renderRoute("/instructor/builds", { role: "instructor" });

    await user.click(screen.getByRole("button", { name: "New build" }));

    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByText(
        "Choose one document and a chunk limit. The build runs as one Qwen job.",
      ),
    ).toBeInTheDocument();
  });
});
