import { useRef, useState } from "react";
import { useLocation, useParams, useSearchParams } from "react-router";

import { ChatEmpty } from "@/components/chat/chat-empty";
import { ChatMessageView } from "@/components/chat/chat-message";
import { Composer } from "@/components/chat/composer";
import { EvidencePanel } from "@/components/chat/evidence-panel";
import { PageLoading } from "@/components/layout/page-states";
import { Badge } from "@/components/ui/badge";
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useT } from "@/lib/i18n";
import type { ModelId, ThinkingLevel } from "@/lib/models";
import { usePreview } from "@/lib/preview/context";
import { PREVIEW_TURNS } from "@/lib/preview/fixtures";
import type { Citation, ConversationTurn } from "@/lib/types";
import { useMediaQuery } from "@/lib/use-media-query";

function turnWithId(turn: ConversationTurn, id: string): ConversationTurn {
  return { ...turn, message: { ...turn.message, id } };
}

export function ChatPage() {
  const t = useT();
  const { sessionId } = useParams();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const draft = (location.state as { draft?: string } | null)?.draft;
  const replay = searchParams.get("replay") === "1";
  const { pageState, setPageState } = usePreview();
  const isNarrow = useMediaQuery("(max-width: 1023px)");

  const [turns, setTurns] = useState<ConversationTurn[]>(
    sessionId ? PREVIEW_TURNS : [],
  );
  const [composer, setComposer] = useState(draft ?? "");
  const [model, setModel] = useState<ModelId>("deepseek-flash");
  const [thinking, setThinking] = useState<ThinkingLevel>("off");
  const [audioAttached, setAudioAttached] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [replaySpeed, setReplaySpeed] = useState("1");
  const nextId = useRef(1);

  const citations = turns.flatMap((turn) => turn.meta?.citations ?? []);
  const activeIndex =
    activeCitation === null ? null : Math.max(citations.indexOf(activeCitation), 0);
  const capabilityError =
    audioAttached && model === "deepseek-flash" ? t.chat.capabilityErrorBody : null;

  function send() {
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
      },
    };
    const assistant = turnWithId(PREVIEW_TURNS[1], `preview-assistant-${id}`);
    setTurns((current) => [...current, userTurn, assistant]);
    setComposer("");
    setActiveCitation(null);
  }

  function retry() {
    setPageState("normal");
  }

  return (
    <div className="flex min-h-0 flex-1">
      <section
        className="flex min-w-0 flex-1 flex-col"
        aria-label={t.a11y.messages}
      >
        {replay ? (
          <div className="flex flex-wrap items-center gap-2 border-b bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{t.chat.replay}</Badge>
            <span>{t.chat.replayBanner}</span>
            <div className="ml-auto flex items-center gap-2">
              <span>{t.chat.replaySpeed}</span>
              <Select value={replaySpeed} onValueChange={setReplaySpeed}>
                <SelectTrigger size="sm" aria-label={t.chat.replaySpeed}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1×</SelectItem>
                  <SelectItem value="2">2×</SelectItem>
                  <SelectItem value="4">4×</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        ) : null}

        {pageState === "loading" ? (
          <div className="min-h-0 flex-1 overflow-y-auto p-6">
            <PageLoading />
          </div>
        ) : turns.length === 0 ? (
          <ChatEmpty onPick={setComposer} />
        ) : (
          <div className="flex min-h-0 flex-1 flex-col">
            <MessageScrollerProvider>
              <MessageScroller className="flex-1">
                <MessageScrollerViewport>
                  <MessageScrollerContent className="mx-auto w-full max-w-3xl px-4 py-6">
                    {turns.map((turn) => (
                      <MessageScrollerItem
                        key={turn.message.id}
                        messageId={turn.message.id}
                        scrollAnchor={turn.message.role === "user"}
                      >
                        <ChatMessageView
                          turn={turn}
                          failed={
                            pageState === "error" && turn.message.role === "assistant"
                          }
                          onOpenCitation={setActiveCitation}
                          onRetry={retry}
                        />
                      </MessageScrollerItem>
                    ))}
                  </MessageScrollerContent>
                </MessageScrollerViewport>
                <MessageScrollerButton />
              </MessageScroller>
            </MessageScrollerProvider>
          </div>
        )}

        <Composer
          value={composer}
          onChange={setComposer}
          onSubmit={send}
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
      </section>

      <aside
        className="hidden w-[380px] shrink-0 flex-col border-l lg:flex"
        aria-label={t.a11y.evidence}
      >
        <div className="border-b px-3 py-2 text-sm font-medium">
          {t.chat.evidenceTitle}
        </div>
        <EvidencePanel
          citations={citations}
          activeIndex={activeIndex}
          onSelect={(index) => setActiveCitation(citations[index] ?? null)}
          className="min-h-0 flex-1"
        />
      </aside>

      {isNarrow ? (
        <Sheet
          open={activeCitation !== null}
          onOpenChange={(open) => {
            if (!open) {
              setActiveCitation(null);
            }
          }}
        >
          <SheetContent side="right" className="w-full p-0 sm:max-w-md">
            <SheetHeader className="border-b">
              <SheetTitle>{t.chat.evidenceTitle}</SheetTitle>
            </SheetHeader>
            <EvidencePanel
              citations={citations}
              activeIndex={activeIndex}
              onSelect={(index) => setActiveCitation(citations[index] ?? null)}
              className="min-h-0 flex-1"
            />
          </SheetContent>
        </Sheet>
      ) : null}
    </div>
  );
}
