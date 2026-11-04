import type { ChatMessage } from "@/lib/types";

/** Keep a few conversations so switching back does not flash a loading state. */
const MAX_CACHED_CONVERSATIONS = 20;

const cache = new Map<string, ChatMessage[]>();

export function readCachedHistory(sessionId: string): ChatMessage[] | null {
  return cache.get(sessionId) ?? null;
}

export function writeCachedHistory(
  sessionId: string,
  messages: ChatMessage[],
): void {
  cache.delete(sessionId);
  cache.set(sessionId, messages);
  if (cache.size > MAX_CACHED_CONVERSATIONS) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) {
      cache.delete(oldest);
    }
  }
}

/** Drop one conversation after a turn changes its stored history. */
export function forgetCachedHistory(sessionId: string): void {
  cache.delete(sessionId);
}

/** Drop every conversation on sign-out or expiry. */
export function clearHistoryCache(): void {
  cache.clear();
}
