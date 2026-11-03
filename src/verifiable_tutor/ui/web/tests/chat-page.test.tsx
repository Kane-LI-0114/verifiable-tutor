import { act, cleanup, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PREVIEW_SESSIONS, PREVIEW_TURNS } from "@/lib/preview/fixtures";
import { renderRoute } from "./render-route";

const SESSION = "/chat/6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8";
const SESSION_ATTENTION = `/chat/${PREVIEW_SESSIONS[1].id}`;
const SESSION_KERNEL = `/chat/${PREVIEW_SESSIONS[2].id}`;

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

  it("loads the attention conversation for its own session", () => {
    renderRoute(SESSION_ATTENTION);

    expect(
      screen.getByText(
        "Why does the softmax in attention subtract the row maximum?",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "How does MPI_Allreduce work, and when should I use it in the GEMM assignment?",
      ),
    ).not.toBeInTheDocument();
  });

  it("switches the conversation body when the route changes to another session", async () => {
    const router = renderRoute(SESSION);

    expect(
      screen.getByText(
        "How does MPI_Allreduce work, and when should I use it in the GEMM assignment?",
      ),
    ).toBeInTheDocument();

    await act(async () => {
      await router.navigate(SESSION_ATTENTION);
    });

    expect(router.state.location.pathname).toBe(SESSION_ATTENTION);
    expect(
      screen.getByText(
        "Why does the softmax in attention subtract the row maximum?",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "How does MPI_Allreduce work, and when should I use it in the GEMM assignment?",
      ),
    ).not.toBeInTheDocument();
  });

  it("clears the conversation body when starting a new chat", async () => {
    const router = renderRoute(SESSION);

    await act(async () => {
      await router.navigate("/chat");
    });

    expect(router.state.location.pathname).toBe("/chat");
    expect(screen.getByText("Ask a course question")).toBeInTheDocument();
    expect(
      screen.queryByText(
        "How does MPI_Allreduce work, and when should I use it in the GEMM assignment?",
      ),
    ).not.toBeInTheDocument();
  });

  it("gives the conversation a heading with the conversation title", () => {
    renderRoute(SESSION);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "How does MPI_Allreduce work?",
      }),
    ).toBeInTheDocument();
  });

  it("keeps a single heading for a session without preview turns", () => {
    renderRoute("/chat/does-not-exist");

    expect(
      screen.getByRole("heading", { level: 1, name: "Ask a course question" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("exposes the labeled chat regions as groups", () => {
    renderRoute(SESSION);

    expect(
      screen.getByRole("group", { name: "Citations" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Work chain" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Answer actions" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Question composer" }),
    ).toBeInTheDocument();
  });

  it("does not send an IME composition when Enter commits it", async () => {
    const user = userEvent.setup();
    renderRoute("/chat");

    const composer = screen.getByLabelText("Your question");
    await user.type(composer, "你好");

    fireEvent.keyDown(composer, { key: "Enter", isComposing: true });

    expect(screen.getByText("Ask a course question")).toBeInTheDocument();
    expect(
      screen.queryByText("你好", { ignore: "textarea" }),
    ).not.toBeInTheDocument();
    expect(composer).toHaveValue("你好");

    fireEvent.keyDown(composer, { key: "Enter" });

    expect(screen.getByText("你好", { ignore: "textarea" })).toBeInTheDocument();
    expect(screen.queryByText("Ask a course question")).not.toBeInTheDocument();
  });

  it("clears the copy feedback timer when the answer unmounts", async () => {
    const user = userEvent.setup();
    const setTimeoutSpy = vi.spyOn(window, "setTimeout");
    const clearTimeoutSpy = vi.spyOn(window, "clearTimeout");

    try {
      renderRoute(SESSION);

      await user.click(
        screen.getByRole("button", { name: "Copy the answer" }),
      );

      const timerIndex = setTimeoutSpy.mock.calls.findIndex(
        (call) => call[1] === 1500,
      );
      expect(timerIndex).toBeGreaterThanOrEqual(0);
      const timerId = setTimeoutSpy.mock.results[timerIndex].value;

      cleanup();

      expect(clearTimeoutSpy).toHaveBeenCalledWith(timerId);
    } finally {
      setTimeoutSpy.mockRestore();
      clearTimeoutSpy.mockRestore();
    }
  });

  it("restores each conversation when switching away and back", async () => {
    const router = renderRoute(SESSION_ATTENTION);

    await act(async () => {
      await router.navigate(SESSION_KERNEL);
    });
    expect(
      screen.getByText(
        "How should I lay out the CUDA kernel for the attention assignment?",
      ),
    ).toBeInTheDocument();

    await act(async () => {
      await router.navigate(SESSION);
    });
    expect(
      screen.getByText(
        "How does MPI_Allreduce work, and when should I use it in the GEMM assignment?",
      ),
    ).toBeInTheDocument();
  });
});
