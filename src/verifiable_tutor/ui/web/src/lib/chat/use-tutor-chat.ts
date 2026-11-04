import { useChat } from "@ai-sdk/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";

import { useSession } from "@/lib/auth/session";
import type { Messages } from "@/lib/i18n/en";
import { type ModelId, type ThinkingLevel } from "@/lib/models";
import { useConversations } from "@/lib/session/conversations";

import { ChatApiError, TutorChatTransport, type TutorSelection } from "./tutor-transport";
import { toConversationTurns, type TutorUIMessage } from "./ui-message";

export interface ChatFailure {
  /** Localized failure copy rendered under the thread. */
  description: string;
  /** The question the retry action puts back in the composer. */
  question: string;
}

export interface TutorChat {
  turns: ReturnType<typeof toConversationTurns>;
  streaming: boolean;
  failure: ChatFailure | null;
  model: ModelId;
  thinking: ThinkingLevel;
  setModel: (model: ModelId) => void;
  setThinking: (thinking: ThinkingLevel) => void;
  send: (text: string) => Promise<void>;
  stop: () => void;
  retryComposerText: () => string | null;
}

function errorDescription(error: unknown, t: Messages): string {
  if (error instanceof ChatApiError) {
    if (error.status === 0) {
      return t.common.networkError;
    }
    if (error.status === 400 || error.status === 422) {
      return t.chat.modelUnavailable;
    }
    if (error.status === 503) {
      return t.chat.modelBusy;
    }
    if (error.status === 404) {
      return t.chat.conversationMissing;
    }
    return t.common.serverError;
  }
  // An error frame from the model stream: the answer did not finish.
  return t.chat.errorBody;
}

/**
 * Live chat state for one conversation.
 *
 * Wraps `useChat` with the project transport, keeps the composer selection in
 * refs so the latest choice is sent, converts UI messages into the page's turn
 * shape, and handles the three failure paths: HTTP errors, in-band stream
 * errors (drop the partial answer), and an expired session.
 */
export function useTutorChat({
  sessionId,
  initialMessages,
  t,
}: {
  sessionId: string | null;
  initialMessages: TutorUIMessage[];
  t: Messages;
}): TutorChat {
  const navigate = useNavigate();
  const conversations = useConversations();
  const { expire } = useSession();

  const [model, setModel] = useState<ModelId>("deepseek-flash");
  const [thinking, setThinking] = useState<ThinkingLevel>("off");
  const selection = useRef<TutorSelection>({ model, thinking });
  selection.current = { model, thinking };

  const conversationId = useRef<string | null>(sessionId);
  const failed = useRef(false);
  const questioned = useRef("");
  const chatRef = useRef<ReturnType<typeof useChat<TutorUIMessage>> | null>(null);
  const [failure, setFailure] = useState<ChatFailure | null>(null);

  // Follow the route when it opens another conversation; a request in flight
  // reads the ref, so a conversation id assigned by the backend is not lost.
  useEffect(() => {
    conversationId.current = sessionId;
  }, [sessionId]);

  const transport = useMemo(
    () =>
      new TutorChatTransport({
        getSessionId: () => conversationId.current,
        getSelection: () => selection.current,
        onConversationId: (id) => {
          conversationId.current = id;
        },
      }),
    [],
  );

  const chat = useChat<TutorUIMessage>({
    id: sessionId ?? "new",
    messages: initialMessages,
    transport,
    onError: (error) => {
      if (error instanceof ChatApiError && error.status === 401) {
        expire();
        return;
      }
      failed.current = true;
      setFailure({
        description: errorDescription(error, t),
        question: questioned.current,
      });
    },
    onFinish: ({ isAbort }) => {
      const active = chatRef.current;
      if (isAbort) {
        // The reader stopped the stream: keep the partial answer in place and
        // do not open a conversation whose answer was never persisted.
        void conversations.refresh();
        return;
      }
      if (failed.current) {
        failed.current = false;
        active?.setMessages((messages) => {
          const last = messages[messages.length - 1];
          return last?.role === "assistant" ? messages.slice(0, -1) : messages;
        });
        void conversations.refresh();
        return;
      }
      void conversations.refresh();
      const id = conversationId.current;
      if (sessionId === null && id !== null) {
        navigate(`/chat/${id}`, { replace: true });
      }
    },
  });

  useEffect(() => {
    chatRef.current = chat;
  }, [chat]);

  const send = useCallback(
    async (text: string) => {
      const question = text.trim();
      if (question.length === 0 || chat.status === "streaming" || chat.status === "submitted") {
        return;
      }
      setFailure(null);
      failed.current = false;
      questioned.current = question;
      await chat.sendMessage({ text: question });
    },
    [chat],
  );

  const stop = useCallback(() => {
    chat.stop();
  }, [chat]);

  const retryComposerText = useCallback(() => {
    const question = failure?.question ?? null;
    setFailure(null);
    return question;
  }, [failure]);

  const turns = useMemo(
    () => toConversationTurns(chat.messages),
    [chat.messages],
  );
  const streaming = chat.status === "submitted" || chat.status === "streaming";

  return {
    turns,
    streaming,
    failure,
    model,
    thinking,
    setModel,
    setThinking,
    send,
    stop,
    retryComposerText,
  };
}
