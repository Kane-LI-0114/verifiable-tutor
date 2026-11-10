import { afterEach, describe, expect, it } from "vitest";

import { streamSpeech } from "@/lib/api/voice";

import { createFetchStub, sseResponse } from "./api-stub";

const ANSWER_MARKDOWN = "## Softmax\n\n**Softmax** is a function.";
const SPEAKABLE_ANSWER = "Softmax\nSoftmax is a function.";
const FRAMES = ["AAABAA==", "AgADAA=="];

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("streamSpeech", () => {
  it("parses frames into pcm16 samples for an answer", async () => {
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech/stream",
        handler: () =>
          sseResponse(
            [{ audio: FRAMES[0] }, { audio: FRAMES[1] }, "[DONE]"],
            { protocol: "plain" },
          ),
      },
    ]);

    const chunks: Int16Array[] = [];
    for await (const chunk of streamSpeech(ANSWER_MARKDOWN)) {
      chunks.push(chunk);
    }

    expect(chunks.map((chunk) => Array.from(chunk))).toEqual([
      [0, 1],
      [2, 3],
    ]);
    expect(stub.calls).toHaveLength(1);
    expect(stub.calls[0].path).toBe("/api/voice/speech/stream");
    expect(stub.calls[0].method).toBe("POST");
    expect(stub.calls[0].init.credentials).toBe("same-origin");
    expect(stub.calls[0].body).toEqual({ text: SPEAKABLE_ANSWER });
  });
});
