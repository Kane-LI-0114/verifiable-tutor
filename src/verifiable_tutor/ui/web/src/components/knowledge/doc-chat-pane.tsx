import { useCallback, useEffect, useRef, useState } from "react";

import { AnswerPending } from "@/components/chat/answer-pending";
import { ChatMessageView } from "@/components/chat/chat-message";
import { Composer } from "@/components/chat/composer";
import { SourceList } from "@/components/chat/source-list";
import { Message, MessageContent } from "@/components/ui/message";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useT } from "@/lib/i18n";
import { useTutorChat } from "@/lib/chat/use-tutor-chat";

const SESSION_KEY_PREFIX = "vt.knowledge.chat.";

function readStoredSession(docId: string): string | null {
  try {
    return window.localStorage?.getItem(`${SESSION_KEY_PREFIX}${docId}`) ?? null;
  } catch {
    return null;
  }
}

function storeSession(docId: string, conversationId: string): void {
  try {
    window.localStorage?.setItem(`${SESSION_KEY_PREFIX}${docId}`, conversationId);
  } catch {
    // The pane still works for this visit when storage is blocked.
  }
}

/**
 * The conversation beside an open document.
 *
 * It is a normal conversation with one addition: every turn carries the file
 * and page being read. The document text itself is not injected yet, and the
 * pane says so rather than implying the answer read the page.
 */
export function DocChatPane({
  docId,
  pageNo,
}: {
  docId: string;
  pageNo: number;
}) {
  const t = useT();
  const [sessionId, setSessionId] = useState<string | null>(() =>
    readStoredSession(docId),
  );
  const [draft, setDraft] = useState("");
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null);
  const toggleSources = useCallback((turnId: string) => {
    setActiveTurnId((current) => (current === turnId ? null : turnId));
  }, []);

  useEffect(() => {
    setSessionId(readStoredSession(docId));
  }, [docId]);

  const chat = useTutorChat({
    sessionId,
    initialMessages: [],
    t,
    documentContext: { doc_id: docId, page_no: pageNo },
    navigateOnFinish: false,
    // Remember the conversation for the next visit, but do not feed the new id
    // back into the hook: a changed useChat id would reset the thread and wipe
    // the answer that just arrived.
    onConversationReady: (conversationId) => {
      storeSession(docId, conversationId);
    },
  });

  const scrollerRef = useRef<HTMLDivElement | null>(null);
  // Only a new turn moves the pane. Watching `chat.streaming` as well used to
  // throw the reader to the bottom when the answer stopped generating.
  useEffect(() => {
    const element = scrollerRef.current;
    if (element !== null) {
      element.scrollTop = element.scrollHeight;
    }
  }, [chat.turns.length]);

  // The assistant turn only exists once the stream starts; until then the pane
  // holds the answer's place open at the end instead of ending at the question.
  const lastTurn = chat.turns[chat.turns.length - 1];
  const awaitingAnswer =
    chat.streaming && lastTurn?.message.role !== "assistant";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <p className="border-b bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        {t.knowledge.chatNotice}
      </p>
      <div ref={scrollerRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3">
        {chat.turns.length === 0 && !awaitingAnswer ? (
          <p className="text-sm text-muted-foreground">{t.knowledge.chatEmpty}</p>
        ) : (
          <>
            {chat.turns.map((turn, index) => (
              <ChatMessageView
                key={turn.message.id}
                turn={turn}
                streaming={chat.streaming && index === chat.turns.length - 1}
                sourcesOpen={activeTurnId === turn.message.id}
                onToggleSources={toggleSources}
              />
            ))}
            {awaitingAnswer ? (
              <Message>
                <MessageContent>
                  <AnswerPending />
                </MessageContent>
              </Message>
            ) : null}
          </>
        )}
      </div>
      {chat.failure ? (
        <p className="border-t px-3 py-2 text-xs text-destructive" role="alert">
          {chat.failure.description}
        </p>
      ) : null}
      <Composer
        value={draft}
        onChange={setDraft}
        onSubmit={() => {
          const text = draft;
          setDraft("");
          setActiveTurnId(null);
          void chat.send(text);
        }}
        onStop={chat.stop}
        streaming={chat.streaming}
        model={chat.model}
        onModelChange={chat.setModel}
        thinking={chat.thinking}
        onThinkingChange={chat.setThinking}
      />
      <Sheet
        open={activeTurnId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActiveTurnId(null);
          }
        }}
      >
        <SheetContent
          id="source-pane"
          side="right"
          className="flex w-full flex-col p-0 sm:max-w-md"
        >
          <SheetHeader className="border-b">
            <SheetTitle>{t.chat.sourcesTitle}</SheetTitle>
          </SheetHeader>
          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            <SourceList
              sources={
                chat.turns.find((turn) => turn.message.id === activeTurnId)?.meta
                  ?.sources ?? []
              }
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
