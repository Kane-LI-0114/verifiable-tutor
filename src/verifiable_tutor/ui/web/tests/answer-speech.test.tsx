import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatMessageView } from "@/components/chat/chat-message";
import { I18nProvider } from "@/lib/i18n";
import type { ConversationTurn } from "@/lib/types";

import { createFetchStub, errorResponse } from "./api-stub";

const ANSWER = "MPI_Allreduce combines values from all ranks.";
// The request carries the speakable form, not the raw Markdown or identifier.
const SPEAKABLE_ANSWER = "MPI Allreduce combines values from all ranks.";

const originalCreateObjectURL = Object.getOwnPropertyDescriptor(
  URL,
  "createObjectURL",
);
const originalRevokeObjectURL = Object.getOwnPropertyDescriptor(
  URL,
  "revokeObjectURL",
);

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

function audioResponse(): Response {
  return new Response(new Uint8Array([1, 2, 3]), {
    status: 200,
    headers: { "content-type": "audio/wav" },
  });
}

let stub: ReturnType<typeof createFetchStub> | null = null;

beforeEach(() => {
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: vi.fn(() => "blob:mock-audio"),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
  stub = createFetchStub([
    {
      method: "POST",
      path: "/api/voice/speech",
      handler: () => audioResponse(),
    },
  ]);
});

afterEach(() => {
  // Unmount while the media spies are still installed, or jsdom reports an
  // unimplemented pause() when the cleanup effect releases the audio element.
  cleanup();
  stub?.restore();
  stub = null;
  vi.restoreAllMocks();
  if (originalCreateObjectURL) {
    Object.defineProperty(URL, "createObjectURL", originalCreateObjectURL);
  } else {
    delete (URL as unknown as { createObjectURL?: unknown }).createObjectURL;
  }
  if (originalRevokeObjectURL) {
    Object.defineProperty(URL, "revokeObjectURL", originalRevokeObjectURL);
  } else {
    delete (URL as unknown as { revokeObjectURL?: unknown }).revokeObjectURL;
  }
});

describe("answer read-aloud", () => {
  it("reads an answer aloud when the speak action is clicked", async () => {
    const user = userEvent.setup();
    const { container } = renderAnswer();

    const button = screen.getByRole("button", { name: "Read aloud" });
    expect(button).toBeEnabled();

    await user.click(button);

    await waitFor(() => expect(stub?.calls).toHaveLength(1));
    const call = stub?.calls[0];
    expect(call?.path).toBe("/api/voice/speech");
    expect(call?.method).toBe("POST");
    expect(call?.init.credentials).toBe("same-origin");
    expect(call?.init.headers).toEqual({ "content-type": "application/json" });
    expect(call?.body).toEqual({ text: SPEAKABLE_ANSWER });

    const audio = container.querySelector("audio");
    expect(audio).not.toBeNull();
    await waitFor(() => expect(audio?.src).toContain("blob:"));
    expect(vi.mocked(HTMLMediaElement.prototype.play)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(URL.createObjectURL)).toHaveBeenCalledTimes(1);
  });

  it("keeps a pending read-aloud from sending a second request", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    stub?.restore();
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: async () => {
          await gate;
          return audioResponse();
        },
      },
    ]);

    const user = userEvent.setup();
    renderAnswer();
    const button = screen.getByRole("button", { name: "Read aloud" });

    await user.click(button);

    await waitFor(() => expect(button).toBeDisabled());
    expect(button).toHaveAttribute("aria-busy", "true");
    fireEvent.click(button);
    expect(stub?.calls).toHaveLength(1);

    await act(async () => {
      release();
    });
    await waitFor(() => expect(button).toBeEnabled());
  });

  it("stops a playing answer when the speak action is clicked again", async () => {
    const user = userEvent.setup();
    const { container } = renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));
    await user.click(await screen.findByRole("button", { name: "Stop" }));

    expect(vi.mocked(HTMLMediaElement.prototype.pause)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(URL.revokeObjectURL)).toHaveBeenCalledWith(
      "blob:mock-audio",
    );
    expect(screen.getByRole("button", { name: "Read aloud" })).toBeEnabled();

    // Playback that finishes on its own also resets the action.
    const audio = container.querySelector("audio");
    expect(audio).not.toBeNull();
    await user.click(screen.getByRole("button", { name: "Read aloud" }));
    await screen.findByRole("button", { name: "Stop" });
    fireEvent(audio as HTMLAudioElement, new Event("ended"));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Read aloud" }),
      ).toBeInTheDocument(),
    );
  });

  it("offers a localized failure message and a retry after a speech error", async () => {
    let attempts = 0;
    stub?.restore();
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => {
          attempts += 1;
          return attempts === 1
            ? errorResponse("The model is temporarily unavailable.", 503)
            : audioResponse();
        },
      },
    ]);
    const user = userEvent.setup();
    const { unmount } = renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Could not read this answer aloud.",
      ),
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(stub?.calls).toHaveLength(2));
    await waitFor(() =>
      expect(vi.mocked(HTMLMediaElement.prototype.play)).toHaveBeenCalledTimes(1),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    unmount();

    stub?.restore();
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () =>
          errorResponse("The model is temporarily unavailable.", 503),
      },
    ]);
    renderAnswer(ANSWER, "zh");
    await user.click(screen.getByRole("button", { name: "朗读" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("无法朗读这条答案。"),
    );
  });

  it("releases the audio URL when the browser blocks playback", async () => {
    vi.mocked(HTMLMediaElement.prototype.play).mockRejectedValueOnce(
      new DOMException("The play request was blocked", "NotAllowedError"),
    );
    const user = userEvent.setup();
    renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Could not read this answer aloud.",
      ),
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
    expect(vi.mocked(URL.revokeObjectURL)).toHaveBeenCalledWith(
      "blob:mock-audio",
    );
  });

  it("releases the audio URL and cancels the request when the answer unmounts", async () => {
    const user = userEvent.setup();
    const playing = renderAnswer();

    await user.click(screen.getByRole("button", { name: "Read aloud" }));
    await screen.findByRole("button", { name: "Stop" });
    playing.unmount();

    expect(vi.mocked(URL.revokeObjectURL)).toHaveBeenCalledWith(
      "blob:mock-audio",
    );
    expect(vi.mocked(URL.revokeObjectURL)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(HTMLMediaElement.prototype.pause)).toHaveBeenCalled();
    expect(stub?.calls[0]?.init.signal?.aborted).toBe(true);

    // A request that is still in flight is cancelled the same way.
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    stub?.restore();
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: async () => {
          await gate;
          return audioResponse();
        },
      },
    ]);
    const pending = renderAnswer();
    await user.click(screen.getByRole("button", { name: "Read aloud" }));
    await waitFor(() => expect(stub?.calls).toHaveLength(1));
    pending.unmount();

    expect(stub?.calls[0]?.init.signal?.aborted).toBe(true);
    await act(async () => {
      release();
    });
  });

  it("stops one answer when another answer starts reading aloud", async () => {
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

    await user.click(
      screen.getAllByRole("button", { name: "Read aloud" })[0],
    );
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Stop" })).toHaveLength(1),
    );

    await user.click(
      screen.getAllByRole("button", { name: "Read aloud" })[0],
    );
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Stop" })).toHaveLength(1),
    );

    expect(screen.getAllByRole("button", { name: "Read aloud" })).toHaveLength(
      1,
    );
    expect(vi.mocked(HTMLMediaElement.prototype.pause)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(URL.revokeObjectURL)).toHaveBeenCalledWith(
      "blob:mock-audio",
    );
    expect(vi.mocked(HTMLMediaElement.prototype.play)).toHaveBeenCalledTimes(2);
    expect(stub?.calls).toHaveLength(2);
  });
});
