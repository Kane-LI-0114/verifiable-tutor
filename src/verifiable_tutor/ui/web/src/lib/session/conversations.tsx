import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { isUnauthorized } from "@/lib/api/client";
import {
  clearHistoryCache,
  readCachedHistory,
  writeCachedHistory,
} from "@/lib/chat/history-cache";
import { sessionsApi } from "@/lib/api/sessions";
import { useSession } from "@/lib/auth/session";
import { usePreview } from "@/lib/preview/context";
import { PREVIEW_SESSIONS } from "@/lib/preview/fixtures";
import type { Conversation } from "@/lib/types";

export type ConversationsStatus = "loading" | "ready" | "error" | "preview";

interface ConversationsValue {
  sessions: Conversation[];
  status: ConversationsStatus;
  refresh: () => Promise<void>;
  /** Warm the history cache for a conversation the reader is about to open. */
  prefetchHistory: (sessionId: string) => void;
}

const ConversationsContext = createContext<ConversationsValue | null>(null);

/**
 * One owner for the sidebar conversation list.
 *
 * It loads once per session, exposes `refresh()` for the chat page after a
 * turn, and returns the preview fixtures untouched in demo mode.
 */
export function ConversationsProvider({ children }: { children: ReactNode }) {
  const { isPreview } = usePreview();
  const { status: sessionStatus, expire } = useSession();
  const [sessions, setSessions] = useState<Conversation[]>([]);
  const [status, setStatus] = useState<ConversationsStatus>(
    isPreview ? "preview" : "loading",
  );
  const requestId = useRef(0);

  const warmHistory = useCallback(
    (sessionId: string) => {
      if (isPreview || sessionStatus !== "authenticated") {
        return;
      }
      if (readCachedHistory(sessionId) !== null) {
        return;
      }
      void sessionsApi
        .messages(sessionId)
        .then((response) => {
          writeCachedHistory(sessionId, response.messages);
        })
        .catch(() => {
          // A warm-up failure is invisible; opening the conversation retries.
        });
    },
    [isPreview, sessionStatus],
  );

  const load = useCallback(async () => {
    if (isPreview) {
      setSessions(PREVIEW_SESSIONS);
      setStatus("preview");
      return;
    }
    if (sessionStatus !== "authenticated") {
      clearHistoryCache();
      setSessions([]);
      setStatus("ready");
      return;
    }
    const current = requestId.current + 1;
    requestId.current = current;
    setStatus("loading");
    try {
      const response = await sessionsApi.list();
      if (requestId.current === current) {
        setSessions(response.sessions);
        setStatus("ready");
        // Warm the listed histories so switching conversations does not flash
        // the loading state for a conversation the reader has not opened yet.
        for (const session of response.sessions) {
          warmHistory(session.id);
        }
      }
    } catch (error) {
      if (requestId.current !== current) {
        return;
      }
      setSessions([]);
      if (isUnauthorized(error)) {
        // A 401 from a later request clears the client session, so the guards
        // send the reader back to the login page instead of a retry state.
        expire();
        return;
      }
      setStatus("error");
    }
  }, [expire, isPreview, sessionStatus, warmHistory]);

  useEffect(() => {
    if (isPreview) {
      setSessions(PREVIEW_SESSIONS);
      setStatus("preview");
      return;
    }
    if (sessionStatus === "authenticated") {
      void load();
      return;
    }
    // A cache entry must not outlive the signed-in user it belongs to.
    clearHistoryCache();
    setSessions([]);
    setStatus(sessionStatus === "loading" ? "loading" : "ready");
  }, [isPreview, load, sessionStatus]);

  const prefetchHistory = warmHistory;

  const value = useMemo<ConversationsValue>(
    () => ({ sessions, status, refresh: load, prefetchHistory }),
    [load, prefetchHistory, sessions, status],
  );

  return (
    <ConversationsContext.Provider value={value}>
      {children}
    </ConversationsContext.Provider>
  );
}

export function useConversations(): ConversationsValue {
  const value = useContext(ConversationsContext);
  if (value === null) {
    throw new Error("useConversations must be used inside ConversationsProvider");
  }
  return value;
}
