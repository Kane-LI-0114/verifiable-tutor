import type { ChatMessage, Conversation } from "@/lib/types";

import { apiFetch } from "./client";

export interface SessionListResponse {
  sessions: Conversation[];
}

export interface SessionMessagesResponse {
  session_id: string;
  messages: ChatMessage[];
}

/** Conversation listing and history; the replay URL is built by the caller. */
export const sessionsApi = {
  list(signal?: AbortSignal): Promise<SessionListResponse> {
    return apiFetch<SessionListResponse>("/api/sessions", { signal });
  },

  messages(sessionId: string, signal?: AbortSignal): Promise<SessionMessagesResponse> {
    return apiFetch<SessionMessagesResponse>(
      `/api/sessions/${encodeURIComponent(sessionId)}/messages`,
      { signal },
    );
  },

  replayUrl(sessionId: string, speed: string): string {
    return `/api/sessions/${encodeURIComponent(sessionId)}/replay?speed=${encodeURIComponent(speed)}`;
  },
};
