import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { Composer } from "@/components/chat/composer";
import { I18nProvider } from "@/lib/i18n";

function Harness({ onSubmit }: { onSubmit: () => void }) {
  const [value, setValue] = useState("");

  return (
    <Composer
      value={value}
      onChange={setValue}
      onSubmit={onSubmit}
      model="deepseek-flash"
      onModelChange={() => {}}
      thinking="off"
      onThinkingChange={() => {}}
    />
  );
}

function renderComposer() {
  const onSubmit = vi.fn();
  render(
    <I18nProvider initialLang="en">
      <Harness onSubmit={onSubmit} />
    </I18nProvider>,
  );
  const textarea = screen.getByLabelText("Your question") as HTMLTextAreaElement;
  return { onSubmit, textarea };
}

describe("composer", () => {
  it("does not send when Enter commits an IME composition", async () => {
    const user = userEvent.setup();
    const { onSubmit, textarea } = renderComposer();

    await user.type(textarea, "你好");
    fireEvent.keyDown(textarea, { key: "Enter", isComposing: true });

    expect(onSubmit).not.toHaveBeenCalled();
    expect(textarea).toHaveValue("你好");
  });

  it("does not send when the IME reports the legacy key code 229", async () => {
    const user = userEvent.setup();
    const { onSubmit, textarea } = renderComposer();

    await user.type(textarea, "你好");
    fireEvent.keyDown(textarea, { key: "Enter", keyCode: 229 });

    expect(onSubmit).not.toHaveBeenCalled();
    expect(textarea).toHaveValue("你好");
  });

  it("sends on a plain Enter", async () => {
    const user = userEvent.setup();
    const { onSubmit, textarea } = renderComposer();

    await user.type(textarea, "How does MPI_Allreduce work?");
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("keeps Shift+Enter for a newline", async () => {
    const user = userEvent.setup();
    const { onSubmit, textarea } = renderComposer();

    await user.type(textarea, "first line");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("exposes the composer as a named group", () => {
    renderComposer();

    expect(
      screen.getByRole("group", { name: "Question composer" }),
    ).toBeInTheDocument();
  });

  it("does not offer a microphone control", () => {
    renderComposer();

    expect(
      screen.queryByRole("button", { name: "Record a question" }),
    ).not.toBeInTheDocument();
  });
});
