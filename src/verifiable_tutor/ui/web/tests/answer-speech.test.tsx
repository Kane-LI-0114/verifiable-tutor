import {
  cleanup,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatMessageView } from "@/components/chat/chat-message";
import { I18nProvider } from "@/lib/i18n";
import type { ConversationTurn } from "@/lib/types";

import { createFetchStub, sseResponse } from "./api-stub";
import { installAudioContextStub } from "./audio-context-stub";

const ANSWER = "MPI_Allreduce combines values from all ranks.";
const SPEAKABLE_ANSWER = "MPI Allreduce combines values from all ranks.";
const FRAMES = ["AAABAA==", "AgADAA=="];

function answerTurn(content: string): ConversationTurn {
  return {
    message: {
      id: "m1",
      sequence: 1,
      role: "assistant",
      content,
      provider: "mimo",
      tier: "pro",
      created_at: "2026-11-10T00:00:00Z",
      reasoning: null,
      model: null,
      thinking: null,
      work_steps: [],
      citations: [],
      tool_calls: [],
    },
  };
}

function renderAnswer(content = ANSWER, lang: "en" | "zh" = "en") {
  return render(
    <I18nProvider initialLang={lang}>
      <ChatMessageView turn={answerTurn(content)} onOpenCitation={() => {}} />
    </I18nProvider>,
  );
}

let stub: ReturnType<typeof createFetchStub> | null = null;
let audio: ReturnType<typeof installAudioContextStub> | null = null;
let releaseGate: (() => void) | null = null;
let streamMode: "success" | "error" = "success";

const STREAM_ERROR =
  "The model is temporarily unavailable. Please try again.";

beforeEach(() => {
  streamMode = "success";
  audio = installAudioContextStub();
  const gate = new Promise<void>((resolve) => {
    releaseGate = resolve;
  });
  stub = createFetchStub([
    {
      method: "POST",
      path: "/api/voice/speech/stream",
      handler: () => {
        if (streamMode === "error") {
          return sseResponse(
            [{ type: "error", errorText: STREAM_ERROR }, "[DONE]"],
            { protocol: "plain" },
          );
        }
        return sseResponse(
          [{ audio: FRAMES[0] }, { audio: FRAMES[1] }, "[DONE]"],
          { protocol: "plain", gate },
        );
      },
    },
  ]);
});

afterEach(() => {
  // Unmount while the Web Audio stub is still installed, before any global
  // restore removes AudioContext from under the cleanup effect.
  cleanup();
  stub?.restore();
  audio?.restore();
  releaseGate?.();
  releaseGate = null;
  stub = null;
  audio = null;
  vi.restoreAllMocks();
});

describe("answer read-aloud", () => {
  it("plays the first frame before the stream ends", async () => {
    const user = userEvent.setup();
    renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));

    await waitFor(() => expect(audio?.starts).toHaveLength(1));
    expect(audio?.context.createBuffer).toHaveBeenCalledWith(1, 2, 24000);
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(stub?.calls).toHaveLength(1);
    expect(stub?.calls[0]?.path).toBe("/api/voice/speech/stream");
    expect(stub?.calls[0]?.body).toEqual({ text: SPEAKABLE_ANSWER });
    expect(audio?.starts).toHaveLength(1);

    releaseGate?.();
    await waitFor(() => expect(audio?.starts).toHaveLength(2));
  });

  it("stops queued sources when the speak action is clicked again", async () => {
    const user = userEvent.setup();
    renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));
    await waitFor(() => expect(audio?.starts).toHaveLength(1));
    await user.click(screen.getByRole("button", { name: "Stop" }));

    expect(audio?.sources[0]?.stop).toHaveBeenCalledTimes(1);
    expect(audio?.context.close).toHaveBeenCalled();
    expect(stub?.calls[0]?.init.signal?.aborted).toBe(true);
    expect(screen.getByRole("button", { name: "Read aloud" })).toBeEnabled();

    releaseGate?.();
    await waitFor(() =>
      expect(audio?.context.createBuffer).toHaveBeenCalledTimes(1),
    );
    expect(audio?.starts).toHaveLength(1);
  });

  it("offers retry after a stream failure", async () => {
    const user = userEvent.setup();
    streamMode = "error";
    renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Could not read this answer aloud.",
      ),
    );
    expect(audio?.context.close).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();

    streamMode = "success";
    releaseGate?.();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(audio?.context.createBuffer).toHaveBeenCalled());
    expect(stub?.calls).toHaveLength(2);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    cleanup();
    streamMode = "error";
    renderAnswer(ANSWER, "zh");
    await user.click(screen.getByRole("button", { name: "朗读" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("无法朗读这条答案。"),
    );
  });

  it("cancels the stream and closes audio when the answer unmounts", async () => {
    const user = userEvent.setup();
    const { unmount } = renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));
    await waitFor(() => expect(audio?.starts).toHaveLength(1));

    unmount();

    expect(stub?.calls[0]?.init.signal?.aborted).toBe(true);
    expect(audio?.sources[0]?.stop).toHaveBeenCalledTimes(1);
    expect(audio?.context.close).toHaveBeenCalled();

    releaseGate?.();
    await waitFor(() =>
      expect(audio?.context.createBuffer).toHaveBeenCalledTimes(1),
    );
    expect(audio?.starts).toHaveLength(1);
  });

  it("keeps one active answer across messages", async () => {
    const user = userEvent.setup();
    render(
      <I18nProvider initialLang="en">
        <ChatMessageView
          turn={answerTurn("First answer.")}
          onOpenCitation={() => {}}
        />
        <ChatMessageView
          turn={answerTurn("Second answer.")}
          onOpenCitation={() => {}}
        />
      </I18nProvider>,
    );

    await user.click(screen.getAllByRole("button", { name: "Read aloud" })[0]);
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Stop" })).toHaveLength(1),
    );

    await user.click(screen.getAllByRole("button", { name: "Read aloud" })[0]);
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Stop" })).toHaveLength(1),
    );
    expect(screen.getAllByRole("button", { name: "Read aloud" })).toHaveLength(
      1,
    );
    expect(audio?.sources[0]?.stop).toHaveBeenCalledTimes(1);
    expect(stub?.calls[0]?.init.signal?.aborted).toBe(true);
    expect(stub?.calls).toHaveLength(2);

    releaseGate?.();
    await waitFor(() => expect(audio?.starts.length).toBeGreaterThan(2));
    audio?.finishAll();
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Read aloud" })).toHaveLength(
        2,
      ),
    );
  });
});
