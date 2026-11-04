import type { ReactNode, UIEvent } from "react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

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
import { readChatScroll, writeChatScroll } from "@/lib/chat/scroll-memory";
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
  /**
   * Conversation id for the remembered thread scroll position. Undefined
   * disables remembering it, which replay and the preview demo want.
   */
  scrollKey?: string;
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
/** How long a debounced scroll write waits after the last scroll event. */
const SCROLL_SAVE_DELAY_MS = 120;
/** How long the thread re-applies its opening position while layout settles. */
const SCROLL_SETTLE_MAX_MS = 1500;

export function ChatSessionShell({
  title,
  scrollKey,
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
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const lastScrollTop = useRef<number | null>(null);
  const saveTimer = useRef<number | null>(null);
  const userInteracted = useRef(false);
  const settleFrame = useRef<number | null>(null);

  const markUserIntent = useCallback(() => {
    userInteracted.current = true;
  }, []);

  const flushScrollPosition = useCallback(() => {
    if (saveTimer.current !== null) {
      window.clearTimeout(saveTimer.current);
      saveTimer.current = null;
    }
    if (scrollKey !== undefined && lastScrollTop.current !== null) {
      writeChatScroll(scrollKey, lastScrollTop.current);
    }
  }, [scrollKey]);

  // The scroller's own end position is measured before off-screen messages have
  // their final height, so a single programmatic scroll can land near the first
  // question. Re-apply the opening position for a few frames until the layout is
  // stable, unless the reader has already taken over the scroll.
  useLayoutEffect(() => {
    if (scrollKey === undefined) {
      return;
    }
    const viewport = viewportRef.current;
    if (viewport === null) {
      return;
    }
    const saved = readChatScroll(scrollKey);
    lastScrollTop.current = null;
    userInteracted.current = false;
    const startedAt = window.performance.now();
    let lastMax = -1;
    let stableFrames = 0;

    const settle = () => {
      settleFrame.current = null;
      const element = viewportRef.current;
      if (element === null || userInteracted.current) {
        return;
      }
      const max = Math.max(0, element.scrollHeight - element.clientHeight);
      // A new conversation opens on its latest answer; a remembered one opens
      // where the reader left it.
      element.scrollTop = saved === null ? max : saved;
      const reached =
        saved === null
          ? Math.abs(element.scrollTop - max) <= 1
          : max >= saved && Math.abs(element.scrollTop - saved) <= 1;
      stableFrames = reached && max === lastMax ? stableFrames + 1 : 0;
      lastMax = max;
      if (
        stableFrames >= 3 ||
        window.performance.now() - startedAt > SCROLL_SETTLE_MAX_MS
      ) {
        return;
      }
      settleFrame.current = window.requestAnimationFrame(settle);
    };
    settleFrame.current = window.requestAnimationFrame(settle);
    return () => {
      if (settleFrame.current !== null) {
        window.cancelAnimationFrame(settleFrame.current);
        settleFrame.current = null;
      }
    };
  }, [scrollKey]);

  // Leaving the page must not lose the position the reader last stopped at.
  useEffect(() => {
    return () => {
      flushScrollPosition();
    };
  }, [flushScrollPosition]);

  function handleScroll(event: UIEvent<HTMLDivElement>) {
    // Only a reader's own scrolling is remembered. The programmatic positioning
    // on mount must not overwrite the stored position with a measured guess.
    if (scrollKey === undefined || !userInteracted.current) {
      return;
    }
    lastScrollTop.current = event.currentTarget.scrollTop;
    if (saveTimer.current !== null) {
      window.clearTimeout(saveTimer.current);
    }
    saveTimer.current = window.setTimeout(() => {
      saveTimer.current = null;
      if (scrollKey !== undefined && lastScrollTop.current !== null) {
        writeChatScroll(scrollKey, lastScrollTop.current);
      }
    }, SCROLL_SAVE_DELAY_MS);
  }

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
          <div
            className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
            onPointerDown={markUserIntent}
          >
            <h1 className="sr-only">{title}</h1>
            <MessageScrollerProvider>
              <MessageScroller className="flex-1">
                <MessageScrollerViewport
                  ref={viewportRef}
                  onScroll={handleScroll}
                  onWheel={markUserIntent}
                  onTouchMove={markUserIntent}
                  onKeyDown={markUserIntent}
                >
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
