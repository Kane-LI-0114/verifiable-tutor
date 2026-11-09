import type {
  KeyboardEvent,
  MouseEvent,
  ReactNode,
  UIEvent,
} from "react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import { AnswerPending } from "@/components/chat/answer-pending";
import { ChatMessageView } from "@/components/chat/chat-message";
import { EvidencePanel } from "@/components/chat/evidence-panel";
import {
  EvidencePane,
  readEvidenceCollapsed,
  writeEvidenceCollapsed,
} from "@/components/chat/evidence-pane";
import { Badge } from "@/components/ui/badge";
import { Message, MessageContent } from "@/components/ui/message";
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
import {
  readChatScroll,
  rememberPendingOpenScroll,
  takePendingOpenScroll,
  writeChatScroll,
} from "@/lib/chat/scroll-memory";
import type { Citation, ConversationTurn } from "@/lib/types";
import { useMediaQuery } from "@/lib/use-media-query";

/**
 * The id the pending answer's placeholder answers to. It is not a message, but
 * the shell anchors scrolling by message id, so the placeholder carries one.
 */
const PENDING_ANSWER_ID = "pending-answer";

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
   * Id of the assistant message currently being generated. The shell keeps a
   * short answer at the bottom and aligns the viewport top to the answer only
   * once it outgrows the viewport; a reader scroll stops all of that. Null or
   * undefined means no answer is in progress.
   */
  generatingMessageId?: string | null;
  /**
   * The question is sent and no answer has arrived yet, so the thread holds the
   * answer's first line open instead of ending at the question. The placeholder
   * takes the place of the generating message as the scrolling anchor, so the
   * view follows the answer from the moment it is awaited.
   */
  awaitingAnswer?: boolean;
  /**
   * Live chat only: the first answer navigates and remounts the thread, so the
   * read position is handed over to the newly created conversation.
   */
  handoffOnFinish?: boolean;
  /**
   * Whether to render the evidence pane and its narrow-screen sheet. Replay has
   * no evidence pane, because a recorded trace has no citations yet.
   */
  showEvidence?: boolean;
}

/**
 * How the thread follows a generating answer:
 * - `short`: the answer still fits the viewport, so it grows at the bottom.
 * - `anchored`: the answer outgrew the viewport, so its top stays at the top.
 * - `following`: the reader asked for the bottom, so the view follows it down.
 * - `free`: the reader scrolled, so no programmatic scroll happens at all.
 * - `idle`: no answer is generating; only the opening position applies.
 */
type ScrollMode = "short" | "anchored" | "following" | "free" | "idle";

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
const SCROLL_SETTLE_MAX_MS = 1000;
/** A scroll event this close to our own target is not a reader scroll. */
const SCROLL_EPSILON_PX = 1;
/** Keys the browser uses to scroll a focused region. */
const SCROLL_KEYS = new Set([
  "ArrowDown",
  "ArrowUp",
  "End",
  "Home",
  "PageDown",
  "PageUp",
  " ",
]);

export function ChatSessionShell({
  title,
  scrollKey,
  turns,
  placeholder,
  banner,
  footer,
  composer,
  turnState,
  generatingMessageId,
  awaitingAnswer = false,
  handoffOnFinish = false,
  showEvidence = true,
}: ChatSessionShellProps) {
  const t = useT();
  const isNarrow = useMediaQuery("(max-width: 1023px)");
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [evidenceCollapsed, setEvidenceCollapsed] = useState<boolean>(() =>
    readEvidenceCollapsed(),
  );
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const lastScrollTop = useRef<number | null>(null);
  const lastKnownTop = useRef(0);
  const saveTimer = useRef<number | null>(null);
  const userInteracted = useRef(false);
  const settleFrame = useRef<number | null>(null);
  const scrollMode = useRef<ScrollMode>("idle");
  const generatingId = useRef<string | null>(null);
  const lastGeneratedId = useRef<string | null>(null);
  const programmaticTop = useRef<number | null>(null);

  const markUserIntent = useCallback(() => {
    userInteracted.current = true;
  }, []);

  /** A wheel or touch scroll hands the thread back to the reader. */
  const markReaderGesture = useCallback(() => {
    markUserIntent();
    if (generatingId.current !== null) {
      scrollMode.current = "free";
    }
  }, [markUserIntent]);

  /** Enter on a citation chip is not a scroll, so only scroll keys count. */
  function handleViewportKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    markUserIntent();
    if (SCROLL_KEYS.has(event.key) && generatingId.current !== null) {
      scrollMode.current = "free";
    }
  }

  /** Move the viewport and remember the target so onScroll can ignore it. */
  function setViewportTop(viewport: HTMLDivElement, top: number) {
    viewport.scrollTop = top;
    // Browsers clamp the value, so record what actually landed.
    lastKnownTop.current = viewport.scrollTop;
    programmaticTop.current = viewport.scrollTop;
  }

  function messageElement(id: string | null): HTMLElement | null {
    const content = contentRef.current;
    if (content === null || id === null) {
      return null;
    }
    for (const child of content.children) {
      if (child instanceof HTMLElement && child.dataset.messageId === id) {
        return child;
      }
    }
    return null;
  }

  /**
   * Only an answer taller than the viewport is worth aligning to its top.
   * A short answer stays at the bottom: pushing it to the top would need an
   * artificial blank area underneath, which reads as an empty broken thread.
   */
  function answerExceedsViewport(): boolean {
    const viewport = viewportRef.current;
    const answer = messageElement(generatingId.current);
    return (
      viewport !== null &&
      answer !== null &&
      answer.getBoundingClientRect().height > viewport.clientHeight
    );
  }

  /** Keep the top of the generating answer level with the top of the thread. */
  function applyAnchor() {
    const viewport = viewportRef.current;
    const anchor = messageElement(generatingId.current);
    if (viewport === null || anchor === null) {
      return;
    }
    const top =
      anchor.getBoundingClientRect().top -
      viewport.getBoundingClientRect().top +
      viewport.scrollTop;
    setViewportTop(viewport, Math.max(0, top));
  }

  /** Follow the end of the thread as the answer grows. */
  function applyBottom() {
    const viewport = viewportRef.current;
    if (viewport === null) {
      return;
    }
    setViewportTop(
      viewport,
      Math.max(0, viewport.scrollHeight - viewport.clientHeight),
    );
  }

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
  // stable, unless the reader has already taken over the scroll. A conversation
  // opened by a finished answer keeps that answer's position across the remount.
  useLayoutEffect(() => {
    if (scrollKey === undefined) {
      return;
    }
    const viewport = viewportRef.current;
    if (viewport === null) {
      return;
    }
    const saved = readChatScroll(scrollKey);
    const last = turns[turns.length - 1];
    const handoff =
      saved === null && last?.message.role === "assistant"
        ? takePendingOpenScroll(last.message.id)
        : null;
    const opening = saved ?? handoff;
    lastScrollTop.current = null;
    userInteracted.current = false;
    const applyOpening = (element: HTMLDivElement, max: number) => {
      setViewportTop(element, opening ?? max);
    };
    // Apply before the first paint; the frames below only correct it while
    // message heights settle. `turns` is deliberately not a dependency.
    applyOpening(
      viewport,
      Math.max(0, viewport.scrollHeight - viewport.clientHeight),
    );
    const startedAt = window.performance.now();
    let lastMax = -1;
    let stableFrames = 0;

    const settle = () => {
      settleFrame.current = null;
      const element = viewportRef.current;
      if (
        element === null ||
        userInteracted.current ||
        generatingId.current !== null
      ) {
        return;
      }
      const max = Math.max(0, element.scrollHeight - element.clientHeight);
      applyOpening(element, max);
      stableFrames = max === lastMax ? stableFrames + 1 : 0;
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

  // Streaming re-renders the thread token by token. A layout effect sees the
  // committed DOM before paint, so the chosen anchor never flickers away. The
  // end of a generation only changes the mode: it must not move the view.
  useLayoutEffect(() => {
    const next =
      generatingMessageId ?? (awaitingAnswer ? PENDING_ANSWER_ID : null);
    const previous = generatingId.current;
    if (next !== previous) {
      generatingId.current = next;
      if (next !== null) {
        lastGeneratedId.current = next;
        scrollMode.current = "short";
      } else {
        if (
          handoffOnFinish &&
          scrollKey === undefined &&
          lastGeneratedId.current !== null &&
          // A question whose answer never started hands over no answer to open.
          lastGeneratedId.current !== PENDING_ANSWER_ID
        ) {
          rememberPendingOpenScroll(
            lastGeneratedId.current,
            viewportRef.current?.scrollTop ?? lastKnownTop.current,
          );
        }
        scrollMode.current = "idle";
      }
    }
    if (scrollMode.current === "short") {
      // Crossing the viewport height switches to the top anchor once. A reader
      // who already scrolled stays in `free` and is never re-anchored.
      if (answerExceedsViewport()) {
        scrollMode.current = "anchored";
        applyAnchor();
      } else {
        applyBottom();
      }
    } else if (scrollMode.current === "anchored") {
      applyAnchor();
    } else if (scrollMode.current === "following") {
      applyBottom();
    }
  });

  // Leaving the page must not lose the position the reader last stopped at.
  useEffect(() => {
    return () => {
      flushScrollPosition();
      if (
        handoffOnFinish &&
        scrollKey === undefined &&
        lastGeneratedId.current !== null
      ) {
        rememberPendingOpenScroll(
          lastGeneratedId.current,
          viewportRef.current?.scrollTop ?? lastKnownTop.current,
        );
      }
    };
  }, [flushScrollPosition, handoffOnFinish, scrollKey]);

  function handleScroll(event: UIEvent<HTMLDivElement>) {
    const viewport = event.currentTarget;
    const top = viewport.scrollTop;
    lastKnownTop.current = top;
    const expected = programmaticTop.current;
    const isOurScroll =
      expected !== null && Math.abs(top - expected) <= SCROLL_EPSILON_PX;
    if (!isOurScroll) {
      programmaticTop.current = null;
      if (generatingId.current !== null) {
        scrollMode.current = "free";
      }
    }
    // Only a reader's own scrolling is remembered. The programmatic positioning
    // on mount must not overwrite the stored position with a measured guess.
    if (scrollKey === undefined || !userInteracted.current) {
      return;
    }
    lastScrollTop.current = top;
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

  /** The arrow asks to follow the answer down, so the bottom becomes the anchor. */
  function handleScrollToEnd(event: MouseEvent<HTMLButtonElement>) {
    if (generatingId.current === null) {
      // An idle thread keeps the scroller's own smooth scroll.
      return;
    }
    event.preventDefault();
    scrollMode.current = "following";
    applyBottom();
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
            {/* The shell owns the streaming anchor, so the primitive only
                measures scrollability and renders the arrow button. */}
            <MessageScrollerProvider autoScroll={false}>
              <MessageScroller className="flex-1">
                <MessageScrollerViewport
                  ref={viewportRef}
                  onScroll={handleScroll}
                  onWheel={markReaderGesture}
                  onTouchMove={markReaderGesture}
                  onKeyDown={handleViewportKeyDown}
                >
                  <MessageScrollerContent
                    ref={contentRef}
                    className="mx-auto w-full max-w-3xl px-4 py-6"
                  >
                    {turns.map((turn, index) => {
                      const state = turnState?.(turn, index);
                      return (
                        <MessageScrollerItem
                          key={turn.message.id}
                          messageId={turn.message.id}
                          scrollAnchor={false}
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
                    {awaitingAnswer ? (
                      <MessageScrollerItem
                        messageId={PENDING_ANSWER_ID}
                        scrollAnchor={false}
                      >
                        <Message>
                          <MessageContent>
                            <AnswerPending />
                          </MessageContent>
                        </Message>
                      </MessageScrollerItem>
                    ) : null}
                  </MessageScrollerContent>
                </MessageScrollerViewport>
                <MessageScrollerButton onClick={handleScrollToEnd} />
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
