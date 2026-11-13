import { HistoryIcon, Loader2Icon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AnswerPending } from "@/components/chat/answer-pending";
import { ChatMessageView } from "@/components/chat/chat-message";
import { Composer } from "@/components/chat/composer";
import { Button } from "@/components/ui/button";
import { Message, MessageContent } from "@/components/ui/message";
import { isAbortError } from "@/lib/api/http";
import { sessionsApi } from "@/lib/api/sessions";
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
 * and page being read. The model opens the page through `read_course_page`
 * when the question needs the text, so the answer is not given the page for
 * free. The conversation belongs to the file: reopening the document continues
 * the same thread, and History folds a previous visit back in on demand.
 */
export function DocChatPane({
  docId,
  pageNo,
}: {
  docId: string;
  pageNo: number;
}) {
  const t = useT();
  const [sessionId] = useState<string | null>(() => readStoredSession(docId));
  // The id used by the History request follows a conversation created in this
  // visit. It is separate from `sessionId` on purpose: feeding a new id back
  // into `useTutorChat` would reset the thread that just received an answer.
  const [historyId, setHistoryId] = useState<string | null>(() =>
    readStoredSession(docId),
  );
  const [draft, setDraft] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyNote, setHistoryNote] = useState<{
    text: string;
    error: boolean;
  } | null>(null);
  const historyRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      historyRequest.current?.abort();
    };
  }, []);

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
      setHistoryId(conversationId);
    },
  });

  async function showHistory() {
    if (historyId === null || historyRequest.current !== null) {
      return;
    }
    const controller = new AbortController();
    historyRequest.current = controller;
    setHistoryLoading(true);
    setHistoryNote(null);
    try {
      const { messages } = await sessionsApi.messages(
        historyId,
        controller.signal,
      );
      if (messages.length === 0) {
        setHistoryNote({ text: t.knowledge.chatHistoryEmpty, error: false });
      } else {
        chat.loadHistory(messages);
      }
    } catch (error) {
      if (!isAbortError(error)) {
        setHistoryNote({ text: t.knowledge.chatHistoryError, error: true });
      }
    } finally {
      if (historyRequest.current === controller) {
        historyRequest.current = null;
      }
      if (!controller.signal.aborted) {
        setHistoryLoading(false);
      }
    }
  }

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
      <div className="flex items-start justify-end gap-2 border-b bg-muted/40 px-3 py-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="-mr-1.5 h-7 shrink-0 gap-1 px-1.5 text-xs font-normal text-muted-foreground"
          aria-label={t.knowledge.chatHistoryLabel}
          aria-busy={historyLoading}
          disabled={historyId === null || historyLoading || chat.streaming}
          onClick={() => void showHistory()}
        >
          {historyLoading ? (
            <Loader2Icon className="size-3.5 animate-spin" />
          ) : (
            <HistoryIcon className="size-3.5" />
          )}
          <span>{t.knowledge.chatHistory}</span>
        </Button>
      </div>
      {historyNote !== null ? (
        <p
          role={historyNote.error ? "alert" : "status"}
          className={
            historyNote.error
              ? "border-b px-3 py-1.5 text-xs text-destructive"
              : "border-b px-3 py-1.5 text-xs text-muted-foreground"
          }
        >
          {historyNote.text}
        </p>
      ) : null}
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
                sourceStyle="disclosure"
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
          setHistoryNote(null);
          void chat.send(text);
        }}
        onStop={chat.stop}
        streaming={chat.streaming}
        model={chat.model}
        onModelChange={chat.setModel}
        thinking={chat.thinking}
        onThinkingChange={chat.setThinking}
        placeholder={t.knowledge.chatPlaceholder}
      />
    </div>
  );
}
