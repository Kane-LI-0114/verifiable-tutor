import { useRef, useState } from "react";
import { useLocation, useParams, useSearchParams } from "react-router";

import { ChatEmpty } from "@/components/chat/chat-empty";
import {
  ChatSessionShell,
  ReplayBanner,
} from "@/components/chat/chat-session-shell";
import { Composer } from "@/components/chat/composer";
import { PageLoading } from "@/components/layout/page-states";
import { useT } from "@/lib/i18n";
import type { ModelId, ThinkingLevel } from "@/lib/models";
import { usePreview } from "@/lib/preview/context";
import {
  PREVIEW_SESSIONS,
  PREVIEW_TURNS,
  previewTurnsFor,
} from "@/lib/preview/fixtures";
import type { ConversationTurn } from "@/lib/types";

function turnWithId(turn: ConversationTurn, id: string): ConversationTurn {
  return { ...turn, message: { ...turn.message, id } };
}

export function PreviewChatPage() {
  const { sessionId } = useParams();
  const location = useLocation();
  const draft = (location.state as { draft?: string } | null)?.draft;

  // /chat and /chat/:sessionId render this page from one element, so React
  // keeps the component mounted across a conversation switch. The key forces
  // a fresh state tree per conversation, which is what makes a switch reset
  // the turns, the composer, and the evidence selection.
  return (
    <ChatSession key={sessionId ?? "new"} sessionId={sessionId} draft={draft} />
  );
}

function ChatSession({
  sessionId,
  draft,
}: {
  sessionId: string | undefined;
  draft: string | undefined;
}) {
  const t = useT();
  const [searchParams] = useSearchParams();
  const replay = searchParams.get("replay") === "1";
  const { pageState, setPageState } = usePreview();

  const [turns, setTurns] = useState<ConversationTurn[]>(() =>
    previewTurnsFor(sessionId),
  );
  const [composer, setComposer] = useState(draft ?? "");
  const [model, setModel] = useState<ModelId>("deepseek-flash");
  const [thinking, setThinking] = useState<ThinkingLevel>("off");
  const [audioAttached, setAudioAttached] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState("1");
  const nextId = useRef(1);

  const conversationTitle =
    PREVIEW_SESSIONS.find((session) => session.id === sessionId)?.title ??
    t.chat.title;
  const capabilityError =
    audioAttached && model === "deepseek-flash" ? t.chat.capabilityErrorBody : null;

  function send(clearCitation: () => void) {
    const text = composer.trim();
    if (!text || capabilityError) {
      return;
    }
    const id = nextId.current++;
    const now = new Date().toISOString();
    const userTurn: ConversationTurn = {
      message: {
        id: `preview-user-${id}`,
        sequence: turns.length + 1,
        role: "user",
        content: text,
        provider: null,
        tier: null,
        created_at: now,
        reasoning: null,
        model: null,
        thinking: null,
        work_steps: [],
        citations: [],
        tool_calls: [],
      },
    };
    const assistant = turnWithId(PREVIEW_TURNS[1], `preview-assistant-${id}`);
    setTurns((current) => [...current, userTurn, assistant]);
    setComposer("");
    clearCitation();
  }

  function retry() {
    setPageState("normal");
  }

  return (
    <ChatSessionShell
      title={conversationTitle}
      turns={turns}
      banner={
        replay ? (
          <ReplayBanner speed={replaySpeed} onSpeedChange={setReplaySpeed} />
        ) : undefined
      }
      placeholder={
        pageState === "loading" ? (
          <div className="min-h-0 flex-1 overflow-y-auto p-6">
            <PageLoading />
          </div>
        ) : turns.length === 0 ? (
          <ChatEmpty onPick={setComposer} />
        ) : undefined
      }
      composer={({ clearCitation }) => (
        <Composer
          value={composer}
          onChange={setComposer}
          onSubmit={() => send(clearCitation)}
          model={model}
          onModelChange={setModel}
          thinking={thinking}
          onThinkingChange={setThinking}
          audioAttached={audioAttached}
          onAttachAudio={() => setAudioAttached(true)}
          onRemoveAudio={() => setAudioAttached(false)}
          capabilityError={capabilityError}
          preview
        />
      )}
      turnState={(turn) => ({
        failed: pageState === "error" && turn.message.role === "assistant",
        onRetry: retry,
      })}
    />
  );
}
