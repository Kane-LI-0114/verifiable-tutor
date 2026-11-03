import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PREVIEW_TURNS } from "@/lib/preview/fixtures";
import { renderRoute } from "./render-route";

const SESSION = "/chat/6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8";

describe("chat page", () => {
  it("renders the conversation, the composer, the work chain, and the evidence panel", () => {
    renderRoute(SESSION);

    expect(
      screen.getByRole("region", { name: "Conversation messages" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Your question")).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: "Evidence panel" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Work chain/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("How does MPI_Allreduce work, and when should I use it in the GEMM assignment?"),
    ).toBeInTheDocument();
  });

  it("opens the cited page in the evidence panel from a citation chip", async () => {
    const user = userEvent.setup();
    renderRoute(SESSION);

    const evidence = screen.getByRole("complementary", { name: "Evidence panel" });
    expect(within(evidence).getByText("Open a citation")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open page 12" }));

    expect(
      within(evidence).getByText("Page 12 of ACS_lecture_2_2026F"),
    ).toBeInTheDocument();
    expect(
      within(evidence).getAllByText(
        "MPI_Allreduce combines values from all ranks and distributes the result to all ranks.",
      ).length,
    ).toBeGreaterThan(0);
  });

  it("expands the work chain to the six document steps", async () => {
    const user = userEvent.setup();
    renderRoute(SESSION);

    await user.click(screen.getByRole("button", { name: /Work chain/ }));

    for (const label of [
      "Understand the question",
      "Retrieve course pages",
      "Verify quoted spans",
      "Apply the disclosure policy",
      "Write the answer",
      "Attach citations",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(
      screen.getByText(/active\.explain-current-topic/),
    ).toBeInTheDocument();
  });

  it("offers the documented model tiers", async () => {
    const user = userEvent.setup();
    renderRoute(SESSION);

    await user.click(screen.getByRole("button", { name: "Model selection" }));

    expect(
      screen.getByRole("menuitemradio", { name: "DeepSeek Flash" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitemradio", { name: "MiMo Flash" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitemradio", { name: "MiMo Pro" }),
    ).toBeInTheDocument();
  });

  it("shows the failure copy and a retry action when the answer fails", () => {
    renderRoute(SESSION, { pageState: "error" });

    expect(screen.getByText("The answer stopped")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText(PREVIEW_TURNS[1].message.content)).not.toBeInTheDocument();
  });

  it("fills the composer from a suggestion and appends a preview answer", async () => {
    const user = userEvent.setup();
    renderRoute("/chat");

    await user.click(
      screen.getByRole("button", { name: "How does MPI_Allreduce work?" }),
    );

    const composer = screen.getByLabelText("Your question");
    expect(composer).toHaveValue("How does MPI_Allreduce work?");

    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      screen.getAllByText("How does MPI_Allreduce work?").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByText(/is a collective that reduces one value per rank/),
    ).toBeInTheDocument();
  });

  it("renders the preview answer from sample data", () => {
    renderRoute(SESSION, { pageState: "loading" });

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });
});
