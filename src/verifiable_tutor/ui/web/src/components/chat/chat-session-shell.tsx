import type { ReactNode } from "react";
import { useState } from "react";

import { ChatMessageView } from "@/components/chat/chat-message";
import { EvidencePanel } from "@/components/chat/evidence-panel";
import {
  EvidencePane,
  readEvidenceCollapsed,
  writeEvidenceCollapsed,
} from "@/components/chat/evidence-pane";
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
import type { Citation, ConversationTurn } from "@/lib/types";
import { useMediaQuery } from "@/lib/use-media-query";

/** The view state one turn adds on top of the shared message composition. */
export interface ChatTurnState {
  streaming?: boolean;
  failed?: boolean;
  onRetry?: () => void;
}

/** Handles the shell exposes to the page's composer area. */
export interface ChatSessionControls {
  /** Clear the active citation, for a page whose send action starts a new question. */
  clearCitation: () => void;
}

export interface ChatSessionShellProps {
  /** Conversation title; rendered as the visually hidden heading above the thread. */
  title: string;
  /** The turns to show; also the source of the citations offered to the evidence pane. */
  turns: ConversationTurn[];
  /** Replaces the thread body, for pages with a loading, empty, or failed state. */
  placeholder?: ReactNode;
  /** Banner above the thread, for the replay banner. */
  banner?: ReactNode;
  /** Alert below the thread, for a failed answer or a failed replay. */
  footer?: ReactNode;
  /** The page's composer. The shell hands back the controls it owns. */
  composer?: (controls: ChatSessionControls) => ReactNode;
  /** Extra view state per turn; the shell does not know how a page tracks progress. */
  turnState?: (turn: ConversationTurn, index: number) => ChatTurnState;
  /**
   * Whether to render the evidence pane and its narrow-screen sheet. Replay has
   * no evidence pane, because a recorded trace has no citations yet.
   */
  showEvidence?: boolean;
}

/**
 * The shared conversation layout: thread, optional banner, optional composer,
 * and the evidence pane with its narrow-screen sheet. The live and preview pages
 * differ in their data source, not in this structure, so both render the shell
 * and keep only their own state and data access.
 *
 * The shell owns the evidence selection and the persisted collapse state, since
 * the citation chips and the pane that answers them live here.
 */
export function ChatSessionShell({
  title,
  turns,
  placeholder,
  banner,
  footer,
  composer,
  turnState,
  showEvidence = true,
}: ChatSessionShellProps) {
  const t = useT();
  const isNarrow = useMediaQuery("(max-width: 1023px)");
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [evidenceCollapsed, setEvidenceCollapsed] = useState<boolean>(() =>
    readEvidenceCollapsed(),
  );

  const citations = turns.flatMap((turn) => turn.meta?.citations ?? []);
  const activeIndex =
    activeCitation === null ? null : Math.max(citations.indexOf(activeCitation), 0);

  function setCollapsed(collapsed: boolean) {
    setEvidenceCollapsed(collapsed);
    writeEvidenceCollapsed(collapsed);
  }

  // A citation chip must reveal the cited page even when the pane is collapsed.
  function openCitation(citation: Citation) {
    setActiveCitation(citation);
    if (evidenceCollapsed) {
      setCollapsed(false);
    }
  }

  function selectCitation(index: number) {
    setActiveCitation(citations[index] ?? null);
  }

  function clearCitation() {
    setActiveCitation(null);
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1">
      <section
        className="flex min-w-0 flex-1 flex-col"
        aria-label={t.a11y.messages}
      >
        {banner}

        {placeholder !== undefined ? (
          placeholder
        ) : (
          <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <h1 className="sr-only">{title}</h1>
            <MessageScrollerProvider>
              <MessageScroller className="flex-1">
                <MessageScrollerViewport>
                  <MessageScrollerContent className="mx-auto w-full max-w-3xl px-4 py-6">
                    {turns.map((turn, index) => {
                      const state = turnState?.(turn, index);
                      return (
                        <MessageScrollerItem
                          key={turn.message.id}
                          messageId={turn.message.id}
                          scrollAnchor={turn.message.role === "user"}
                        >
                          <ChatMessageView
                            turn={turn}
                            streaming={state?.streaming}
                            failed={state?.failed}
                            onRetry={state?.onRetry}
                            onOpenCitation={openCitation}
                          />
                        </MessageScrollerItem>
                      );
                    })}
                  </MessageScrollerContent>
                </MessageScrollerViewport>
                <MessageScrollerButton />
              </MessageScroller>
            </MessageScrollerProvider>
          </div>
        )}

        {footer}

        {composer?.({ clearCitation })}
      </section>

      {showEvidence ? (
        <>
          <EvidencePane
            citations={citations}
            activeIndex={activeIndex}
            onSelect={selectCitation}
            collapsed={evidenceCollapsed}
            onCollapsedChange={setCollapsed}
          />

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
                  onSelect={selectCitation}
                  className="min-h-0 flex-1"
                />
              </SheetContent>
            </Sheet>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

/**
 * The replay banner with its speed control. Live replay restarts the recorded
 * stream at the new speed; the preview demo only keeps the selected speed.
 */
export function ReplayBanner({
  speed,
  onSpeedChange,
}: {
  speed: string;
  onSpeedChange: (speed: string) => void;
}) {
  const t = useT();

  return (
    <div className="flex flex-wrap items-center gap-2 border-b bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
      <Badge variant="secondary">{t.chat.replay}</Badge>
      <span>{t.chat.replayBanner}</span>
      <div className="ml-auto flex items-center gap-2">
        <span>{t.chat.replaySpeed}</span>
        <Select value={speed} onValueChange={onSpeedChange}>
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
  );
}
