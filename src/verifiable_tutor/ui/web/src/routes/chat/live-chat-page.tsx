import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router";

import { ChatEmpty } from "@/components/chat/chat-empty";
import {
  ChatSessionShell,
  ReplayBanner,
} from "@/components/chat/chat-session-shell";
import { Composer } from "@/components/chat/composer";
import { PageEmpty, PageError, PageLoading } from "@/components/layout/page-states";
import { ApiError } from "@/lib/api/client";
import { sessionsApi } from "@/lib/api/sessions";
import { useSession } from "@/lib/auth/session";
import { useReplayStream } from "@/lib/chat/use-replay-stream";
import { useTutorChat } from "@/lib/chat/use-tutor-chat";
import {
  toConversationTurns,
  toTutorMessages,
  type TutorUIMessage,
} from "@/lib/chat/ui-message";
import { useT } from "@/lib/i18n";
import { useConversations } from "@/lib/session/conversations";
import type { ChatMessage, ConversationTurn } from "@/lib/types";

type HistoryStatus = "loading" | "ready" | "error" | "missing";

interface HistoryValue {
  status: HistoryStatus;
  /** The stored rows for this conversation, which carry the turn metadata. */
  messages: ChatMessage[];
  turns: ConversationTurn[];
  retry: () => void;
}

/**
 * Load one conversation's stored messages. The composer only mounts after the
 * history is ready, so `useChat` starts from complete state.
 */
function useSessionHistory(sessionId: string | null): HistoryValue {
  const { expire } = useSession();
  const [status, setStatus] = useState<HistoryStatus>(
    sessionId === null ? "ready" : "loading",
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => {
    setAttempt((current) => current + 1);
  }, []);

  useEffect(() => {
    if (sessionId === null) {
      setStatus("ready");
      setMessages([]);
      return;
    }
    let cancelled = false;
    setStatus("loading");
    sessionsApi
      .messages(sessionId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setMessages(response.messages);
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiError && error.status === 401) {
          expire();
          return;
        }
        setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [attempt, expire, sessionId]);

  return {
    status,
    messages,
    turns: toConversationTurns(toTutorMessages(messages), messages),
    retry,
  };
}

export function LiveChatPage() {
  const { sessionId } = useParams();
  const [searchParams] = useSearchParams();
  const t = useT();
  const replay = searchParams.get("replay") === "1";

  if (replay) {
    if (sessionId === undefined) {
      return (
        <div className="flex min-h-0 flex-1 items-center justify-center p-6">
          <PageEmpty
            title={t.chat.replayNeedsConversation}
            description={t.chat.replayErrorBody}
          />
        </div>
      );
    }
    return <ReplayChatPage key={sessionId} sessionId={sessionId} />;
  }

  if (sessionId === undefined) {
    return (
      <LiveChatSession
        key="new"
        sessionId={null}
        initialMessages={[]}
        storedMessages={[]}
      />
    );
  }
  return <ConversationChatPage key={sessionId} sessionId={sessionId} />;
}

/**
 * The gate both conversation views pass: one stored-history load with the same
 * loading, missing, and error copy, retry action, and "New question" link.
 */
function ChatHistoryGate({
  sessionId,
  children,
}: {
  sessionId: string;
  children: (history: HistoryValue) => ReactNode;
}) {
  const t = useT();
  const history = useSessionHistory(sessionId);

  if (history.status === "loading") {
    return (
      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        <PageLoading />
      </div>
    );
  }
  if (history.status === "missing") {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-6">
        <PageEmpty
          title={t.chat.conversationMissing}
          description={t.chat.historyErrorBody}
          action={
            <Link to="/chat" className="text-sm underline underline-offset-4">
              {t.nav.newChat}
            </Link>
          }
        />
      </div>
    );
  }
  if (history.status === "error") {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-6">
        <div className="w-full max-w-xl">
          <PageError
            title={t.chat.historyErrorTitle}
            description={t.chat.historyErrorBody}
            onRetry={history.retry}
          />
        </div>
      </div>
    );
  }
  return <>{children(history)}</>;
}

function ConversationChatPage({ sessionId }: { sessionId: string }) {
  return (
    <ChatHistoryGate sessionId={sessionId}>
      {(history) => (
        <LiveChatSession
          key={sessionId}
          sessionId={sessionId}
          initialMessages={toTutorMessages(history.messages)}
          storedMessages={history.messages}
        />
      )}
    </ChatHistoryGate>
  );
}

function ReplayChatPage({ sessionId }: { sessionId: string }) {
  return (
    <ChatHistoryGate sessionId={sessionId}>
      {(history) => (
        <ReplaySession
          key={sessionId}
          sessionId={sessionId}
          historyTurns={history.turns}
        />
      )}
    </ChatHistoryGate>
  );
}

function conversationTitle(
  sessions: { id: string; title: string | null }[],
  sessionId: string | null,
  fallback: string,
): string {
  if (sessionId === null) {
    return fallback;
  }
  return sessions.find((session) => session.id === sessionId)?.title ?? fallback;
}

function LiveChatSession({
  sessionId,
  initialMessages,
  storedMessages,
}: {
  sessionId: string | null;
  initialMessages: TutorUIMessage[];
  storedMessages: ChatMessage[];
}) {
  const t = useT();
  const { sessions } = useConversations();
  const chat = useTutorChat({ sessionId, initialMessages, storedMessages, t });
  const [composer, setComposer] = useState("");
  const title = conversationTitle(sessions, sessionId, t.chat.title);

  function retryFailure() {
    const question = chat.retryComposerText();
    if (question !== null) {
      setComposer(question);
    }
  }

  async function submit(clearCitation: () => void) {
    const text = composer.trim();
    if (text.length === 0 || chat.streaming) {
      return;
    }
    setComposer("");
    clearCitation();
    await chat.send(text);
  }

  return (
    <ChatSessionShell
      title={title}
      scrollKey={sessionId ?? undefined}
      turns={chat.turns}
      placeholder={
        chat.turns.length === 0 && !chat.streaming ? (
          <ChatEmpty onPick={setComposer} />
        ) : undefined
      }
      footer={
        chat.failure ? (
          <div className="mx-auto w-full max-w-3xl px-4 pb-3">
            <PageError
              title={t.chat.errorTitle}
              description={chat.failure.description}
              onRetry={retryFailure}
            />
          </div>
        ) : undefined
      }
      composer={({ clearCitation }) => (
        <Composer
          value={composer}
          onChange={setComposer}
          onSubmit={() => {
            void submit(clearCitation);
          }}
          onStop={chat.stop}
          streaming={chat.streaming}
          model={chat.model}
          onModelChange={chat.setModel}
          thinking={chat.thinking}
          onThinkingChange={chat.setThinking}
          preview={false}
        />
      )}
      turnState={(turn, index) => ({
        streaming:
          chat.streaming &&
          index === chat.turns.length - 1 &&
          turn.message.role === "assistant" &&
          turn.message.content === "",
      })}
    />
  );
}

function ReplaySession({
  sessionId,
  historyTurns,
}: {
  sessionId: string;
  historyTurns: ConversationTurn[];
}) {
  const t = useT();
  const { sessions } = useConversations();
  const [speed, setSpeed] = useState("1");
  const replay = useReplayStream({ sessionId, speed, historyTurns, t });
  const title = conversationTitle(sessions, sessionId, t.chat.title);

  const visibleTurns = replay.turns.filter(
    (turn) =>
      turn.message.role === "user" ||
      turn.message.content.length > 0 ||
      (turn.meta?.work_steps.length ?? 0) > 0 ||
      (turn.meta?.reasoning.length ?? 0) > 0,
  );

  const replayFailed = replay.status === "error" && replay.errorDescription === null;

  return (
    <ChatSessionShell
      title={title}
      turns={visibleTurns}
      showEvidence={false}
      banner={<ReplayBanner speed={speed} onSpeedChange={setSpeed} />}
      placeholder={
        replay.status === "error" && replay.errorDescription !== null ? (
          <div className="mx-auto flex w-full max-w-xl flex-1 items-center p-6">
            <PageError
              title={t.chat.replayErrorTitle}
              description={replay.errorDescription}
              onRetry={replay.retry}
            />
          </div>
        ) : undefined
      }
      footer={
        replayFailed ? (
          <div className="mx-auto w-full max-w-3xl px-4 pb-4">
            <PageError title={t.chat.errorTitle} description={t.chat.errorBody} />
          </div>
        ) : undefined
      }
    />
  );
}
