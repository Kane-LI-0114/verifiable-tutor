import { afterEach, describe, expect, it, vi } from "vitest";

import { synthesizeSpeech } from "@/lib/api/voice";

import { createFetchStub, errorResponse } from "./api-stub";

const ANSWER_MARKDOWN = [
  "## Softmax",
  "",
  "**Softmax** turns logits into probabilities: $\\sigma(z_i) = e^{z_i} / \\sum_j e^{z_j}$.",
  "",
  "```python",
  "def softmax(z):",
  "    return np.exp(z) / np.sum(np.exp(z))",
  "```",
  "",
  "See [the lecture notes](https://example.test/notes) for the derivation.",
  "",
  "- Every entry is positive.",
  "- The probabilities always sum to one.",
].join("\n");

const EXPECTED_SPEECH_TEXT = [
  "Softmax",
  "Softmax turns logits into probabilities: sigma(z i) = e z i / sum j e z j.",
  "def softmax(z):",
  "return np.exp(z) / np.sum(np.exp(z))",
  "See the lecture notes for the derivation.",
  "Every entry is positive.",
  "The probabilities always sum to one.",
].join("\n");

function audioResponse(): Response {
  return new Response(new Uint8Array([1, 2, 3]), {
    status: 200,
    headers: { "content-type": "audio/wav" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("synthesizeSpeech", () => {
  it("turns a rejected speech request into an ApiError with the backend detail", async () => {
    const blank = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => errorResponse("text must not be empty", 400),
      },
    ]);
    await expect(synthesizeSpeech("")).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
      detail: "text must not be empty",
    });
    blank.restore();

    const unsigned = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => errorResponse("not signed in", 401),
      },
    ]);
    await expect(synthesizeSpeech("hello")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      detail: "not signed in",
    });
    unsigned.restore();
  });

  it("reports an unreachable speech backend as a network error", async () => {
    createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => {
          throw new TypeError("fetch failed");
        },
      },
    ]);

    await expect(synthesizeSpeech("hello")).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
      detail: "network error",
    });
  });

  it("forwards the caller's abort signal and keeps a real abort intact", async () => {
    const controller = new AbortController();
    const completed = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => audioResponse(),
      },
    ]);
    await synthesizeSpeech("hello", controller.signal);
    expect(completed.calls[0].init.signal).toBe(controller.signal);
    completed.restore();

    const abort = new DOMException("The operation was aborted.", "AbortError");
    const cancelled = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => {
          throw abort;
        },
      },
    ]);
    await expect(synthesizeSpeech("hello", controller.signal)).rejects.toBe(
      abort,
    );
    cancelled.restore();
  });

  it("sends a speakable plain text version of an answer without truncating it", async () => {
    const stub = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => audioResponse(),
      },
    ]);

    await synthesizeSpeech(ANSWER_MARKDOWN);

    const sent = (stub.calls[0].body as { text: string }).text;
    expect(sent).toEqual(EXPECTED_SPEECH_TEXT);
    expect(sent).not.toContain("```");
    expect(sent).not.toContain("**");
    expect(sent).toContain("The probabilities always sum to one.");
    stub.restore();
  });
});
