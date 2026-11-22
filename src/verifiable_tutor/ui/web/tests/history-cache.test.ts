import { describe, expect, it } from "vitest";

import {
  clearHistoryCache,
  forgetCachedHistory,
  readCachedHistory,
  writeCachedHistory,
} from "@/lib/chat/history-cache";
import type { ChatMessage } from "@/lib/types";

function message(id: string): ChatMessage {
  return {
    id,
    sequence: 1,
    role: "assistant",
    content: `answer ${id}`,
    provider: "deepseek",
    tier: "flash",
    created_at: "2026-11-03T09:12:00+00:00",
    reasoning: null,
    model: "deepseek-flash",
    thinking: "off",
    work_steps: [],
    citations: [],
    sources: [],
    tool_calls: [],
  };
}

describe("conversation history cache", () => {
  it("returns null for a conversation that was never loaded", () => {
    expect(readCachedHistory("session-a")).toBeNull();
  });

  it("round-trips a loaded conversation and forgets one entry", () => {
    writeCachedHistory("session-a", [message("message-a")]);
    writeCachedHistory("session-b", [message("message-b")]);

    expect(readCachedHistory("session-a")?.[0].content).toBe("answer message-a");
    expect(readCachedHistory("session-b")?.[0].content).toBe("answer message-b");

    forgetCachedHistory("session-a");
    expect(readCachedHistory("session-a")).toBeNull();
    expect(readCachedHistory("session-b")).not.toBeNull();
  });

  it("clears every conversation on sign-out", () => {
    writeCachedHistory("session-a", [message("message-a")]);
    writeCachedHistory("session-b", [message("message-b")]);

    clearHistoryCache();

    expect(readCachedHistory("session-a")).toBeNull();
    expect(readCachedHistory("session-b")).toBeNull();
  });

  it("keeps only the most recently used conversations", () => {
    for (let index = 0; index < 21; index += 1) {
      writeCachedHistory(`session-${index}`, [message(`message-${index}`)]);
    }

    expect(readCachedHistory("session-0")).toBeNull();
    expect(readCachedHistory("session-20")).not.toBeNull();
  });
});
