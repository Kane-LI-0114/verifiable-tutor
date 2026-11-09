/** Browser storage key prefix for one conversation's thread scroll position. */
export const CHAT_SCROLL_KEY_PREFIX = "vt.chat.scroll.";

export function chatScrollKey(sessionId: string): string {
  return `${CHAT_SCROLL_KEY_PREFIX}${sessionId}`;
}

/**
 * Read the scroll offset a conversation was left at.
 *
 * The value is per conversation in local storage. Missing, unreadable, or
 * invalid values return null, so the thread keeps its normal end position.
 */
export function readChatScroll(sessionId: string): number | null {
  try {
    const raw =
      typeof window === "undefined"
        ? null
        : window.localStorage?.getItem(chatScrollKey(sessionId));
    if (raw === null || raw === undefined) {
      return null;
    }
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) {
      return null;
    }
    const top = (parsed as Record<string, unknown>).top;
    return typeof top === "number" && Number.isFinite(top) && top >= 0
      ? top
      : null;
  } catch {
    return null;
  }
}

/**
 * The first answer of a new conversation ends by navigating, which remounts
 * the thread under its new conversation id. Carry the offset the reader was at
 * across that one mount, so the finished answer is not thrown to the bottom.
 */
let pendingOpenScroll: { messageId: string; top: number } | null = null;

export function rememberPendingOpenScroll(messageId: string, top: number): void {
  pendingOpenScroll = { messageId, top };
}

/** Consume the handoff only for a thread that shows the same last answer. */
export function takePendingOpenScroll(messageId: string | null): number | null {
  const pending = pendingOpenScroll;
  pendingOpenScroll = null;
  if (pending === null || messageId === null || pending.messageId !== messageId) {
    return null;
  }
  return pending.top >= 0 && Number.isFinite(pending.top) ? pending.top : null;
}

/** Store the scroll offset of one conversation; unavailable storage is ignored. */
export function writeChatScroll(sessionId: string, top: number): void {
  try {
    if (
      typeof window === "undefined" ||
      !Number.isFinite(top) ||
      top < 0
    ) {
      return;
    }
    window.localStorage?.setItem(
      chatScrollKey(sessionId),
      JSON.stringify({ top: Math.round(top) }),
    );
  } catch {
    // Private mode or quota refusal: scrolling still works for this mount.
  }
}
