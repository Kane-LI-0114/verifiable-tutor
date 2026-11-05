import { type ChatTransport, type UIMessageChunk } from "ai";

import { detailFromText, isAbortError } from "@/lib/api/http";
import { MODEL_OPTIONS, type ModelId, type ThinkingLevel } from "@/lib/models";

import { toChunkStream } from "./stream";
import { lastUserText, type ModelProviderTier, type TutorUIMessage } from "./ui-message";

/** A chat failure that carries the HTTP status, or 0 when the request never ran. */
export class ChatApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ChatApiError";
    this.status = status;
    this.detail = detail;
  }
}

export interface TutorSelection {
  model: ModelId;
  thinking: ThinkingLevel;
}

export interface TutorTransportOptions {
  /**
   * The conversation the next request belongs to; null starts a new one.
   * Read at request time so a conversation the backend assigned to a failed
   * turn is reused instead of orphaned.
   */
  getSessionId: () => string | null;
  /** Read the composer selection when the request is built, not at mount. */
  getSelection: () => TutorSelection;
  /** Called with the conversation id the backend assigned or reused. */
  onConversationId: (conversationId: string) => void;
  /**
   * The document and page open in the knowledge-base preview, read at request
   * time. Null for a normal chat turn.
   */
  getDocumentContext?: () => { doc_id: string; page_no: number | null } | null;
}

/**
 * Attach the request-time provider and tier to the streamed assistant message.
 *
 * The backend persists them with the answer but does not stream them; the AI
 * SDK reads them from the `start` chunk, so the badge keeps the model that
 * actually answered even after the composer selection changes.
 */
function withMessageMetadata(
  stream: ReadableStream<UIMessageChunk>,
  metadata: ModelProviderTier,
): ReadableStream<UIMessageChunk> {
  return stream.pipeThrough(
    new TransformStream<UIMessageChunk, UIMessageChunk>({
      transform(chunk, controller) {
        controller.enqueue(
          chunk.type === "start" ? { ...chunk, messageMetadata: metadata } : chunk,
        );
      },
    }),
  );
}

/**
 * Chat transport for the project backend.
 *
 * The backend accepts a single newest message plus the session id and owns the
 * conversation history, so the transport maps the last user text instead of the
 * default `{messages}` body. The AI SDK `useChat` state machine, streaming
 * parser, and `data-step` parts are reused unchanged.
 */
export class TutorChatTransport implements ChatTransport<TutorUIMessage> {
  private readonly options: TutorTransportOptions;

  constructor(options: TutorTransportOptions) {
    this.options = options;
  }

  async sendMessages({
    messages,
    abortSignal,
  }: Parameters<ChatTransport<TutorUIMessage>["sendMessages"]>[0]): Promise<
    ReadableStream<UIMessageChunk>
  > {
    const selection = this.options.getSelection();
    const model =
      MODEL_OPTIONS.find((option) => option.id === selection.model) ??
      MODEL_OPTIONS[0];

    let response: Response;
    try {
      response = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        credentials: "same-origin",
        signal: abortSignal,
        body: JSON.stringify({
          message: lastUserText(messages),
          session_id: this.options.getSessionId(),
          provider: model.provider,
          tier: model.tier,
          thinking: selection.thinking,
          document_context: this.options.getDocumentContext?.() ?? undefined,
        }),
      });
    } catch (error) {
      if (isAbortError(error)) {
        throw error;
      }
      throw new ChatApiError(0, "network error");
    }

    const conversationId = response.headers.get("x-conversation-id");
    if (conversationId !== null) {
      this.options.onConversationId(conversationId);
    }

    if (!response.ok) {
      throw new ChatApiError(response.status, detailFromText(await response.text()));
    }
    if (response.body === null) {
      throw new ChatApiError(0, "empty response body");
    }
    return withMessageMetadata(toChunkStream(response.body), {
      provider: model.provider,
      tier: model.tier,
    });
  }

  async reconnectToStream(): Promise<ReadableStream<UIMessageChunk> | null> {
    return null;
  }
}
