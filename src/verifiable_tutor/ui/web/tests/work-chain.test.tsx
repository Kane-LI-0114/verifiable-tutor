import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { WorkChain } from "@/components/chat/work-chain";
import { I18nProvider } from "@/lib/i18n";
import type { ToolCall, WorkChainEvent, WorkStep } from "@/lib/types";

function step(name: WorkStep["step"], overrides: Partial<WorkStep> = {}): WorkStep {
  return { id: name, step: name, status: "done", duration_ms: 1, ...overrides };
}

const TOOL_CALL: ToolCall = {
  name: "search_course",
  command: [],
  exit_code: 0,
  output: "one chunk",
  status: "done",
};

function renderChain(steps: WorkStep[], events: WorkChainEvent[]) {
  render(
    <I18nProvider initialLang="en">
      <WorkChain steps={steps} policy="active" events={events} />
    </I18nProvider>,
  );
}

async function expand() {
  await userEvent.click(screen.getByRole("button", { name: /Work chain/ }));
}

describe("work chain", () => {
  it("shows one section per actual step in phase order and hides missing steps", async () => {
    renderChain(
      [
        step("generate"),
        step("retrieve", { detail: "Hybrid retrieval returned 5 pages." }),
        step("understand", { detail: "Parsed the question." }),
        step("decide"),
      ],
      [
        { kind: "reasoning", reasoning: "Think first.", step_id: "generate" },
        { kind: "tool_call", tool_call: TOOL_CALL, step_id: "retrieve" },
      ],
    );
    await expand();

    const understand = screen.getByText("Understand the question");
    const retrieve = screen.getByText("Retrieve course pages");
    const decide = screen.getByText("Apply the disclosure policy");
    const generate = screen.getByText("Write the answer");

    expect(
      understand.compareDocumentPosition(retrieve) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      retrieve.compareDocumentPosition(decide) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      decide.compareDocumentPosition(generate) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByText("Attach citations")).not.toBeInTheDocument();
  });

  it("keeps a step with no events and shows its detail", async () => {
    renderChain(
      [step("understand", { detail: "Parsed the question." }), step("generate")],
      [],
    );
    await expand();

    expect(screen.getByText("Understand the question")).toBeInTheDocument();
    expect(screen.getByText("Parsed the question.")).toBeInTheDocument();
    expect(screen.getByText("Write the answer")).toBeInTheDocument();
  });

  it("groups each event under its step section", async () => {
    renderChain(
      [step("retrieve"), step("generate")],
      [
        { kind: "reasoning", reasoning: "Think first.", step_id: "generate" },
        { kind: "tool_call", tool_call: TOOL_CALL, step_id: "retrieve" },
      ],
    );
    await expand();

    const retrieve = screen.getByRole("region", {
      name: /Retrieve course pages/,
    });
    const generate = screen.getByRole("region", {
      name: /Write the answer/,
    });
    expect(within(retrieve).getByText("Tool call: search_course")).toBeInTheDocument();
    expect(within(generate).getByText("Think first.")).toBeInTheDocument();
    expect(within(retrieve).queryByText("Think first.")).not.toBeInTheDocument();
  });

  it("renders an event whose step id has no step row flat", async () => {
    renderChain(
      [step("generate")],
      [{ kind: "tool_call", tool_call: TOOL_CALL, step_id: "unknown-step" }],
    );
    await expand();

    expect(screen.getByText("Tool call: search_course")).toBeInTheDocument();
    expect(screen.queryByText("Verify quoted spans")).not.toBeInTheDocument();
  });

  it("renders events without a step flat for legacy rows", async () => {
    renderChain(
      [step("generate")],
      [{ kind: "reasoning", reasoning: "Legacy thought." }],
    );
    await expand();

    expect(screen.getByText("Legacy thought.")).toBeInTheDocument();
    expect(screen.queryByText("Verify quoted spans")).not.toBeInTheDocument();
  });
});
