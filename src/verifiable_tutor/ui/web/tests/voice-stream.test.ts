import { afterEach, describe, expect, it } from "vitest";

import { streamSpeech } from "@/lib/api/voice";

import { createFetchStub, sseResponse } from "./api-stub";

const ANSWER_MARKDOWN = "## Softmax\n\n**Softmax** is a function.";
const SPEAKABLE_ANSWER = "Softmax\nSoftmax is a function.";
const FRAMES = ["AAABAA==", "AgADAA=="];

let stub: ReturnType<typeof createFetchStub> | null = null;

function abortableResponse(signal: AbortSignal | null | undefined): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ audio: FRAMES[0] })}\n\n`),
      );
      signal?.addEventListener(
        "abort",
        () =>
          controller.error(
            new DOMException("The operation was aborted.", "AbortError"),
          ),
        { once: true },
      );
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

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

  it("aborts the request without playing later frames", async () => {
    const controller = new AbortController();
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech/stream",
        handler: (call) => abortableResponse(call.init.signal),
      },
    ]);

    const frames = streamSpeech(ANSWER_MARKDOWN, controller.signal);
    const first = await frames.next();
    expect(Array.from(first.value ?? [])).toEqual([0, 1]);
    expect(stub.calls[0].init.signal).toBe(controller.signal);

    controller.abort();
    await expect(frames.next()).rejects.toMatchObject({ name: "AbortError" });
  });
});
