import {
  parseJsonEventStream,
  uiMessageChunkSchema,
  type UIMessageChunk,
} from "ai";

/**
 * Parse the backend AI SDK UI message stream into protocol chunks.
 *
 * The backend emits `start`, `data-step` (a custom data part), reasoning and
 * text deltas, `finish`, and `error` frames, then `data: [DONE]`, which the AI
 * SDK parser skips. A malformed frame throws, so live chat and replay fail the
 * same way instead of each reimplementing the parse loop.
 */
export function toChunkStream(
  stream: ReadableStream<Uint8Array>,
): ReadableStream<UIMessageChunk> {
  return parseJsonEventStream({ stream, schema: uiMessageChunkSchema }).pipeThrough(
    new TransformStream({
      transform(chunk, controller) {
        if (!chunk.success) {
          throw chunk.error;
        }
        controller.enqueue(chunk.value);
      },
    }),
  );
}
