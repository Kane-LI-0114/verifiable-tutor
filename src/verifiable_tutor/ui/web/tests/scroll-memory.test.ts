import { beforeEach, describe, expect, it } from "vitest";

import {
  chatScrollKey,
  readChatScroll,
  writeChatScroll,
} from "@/lib/chat/scroll-memory";

import { installMemoryStorage } from "./memory-storage";

beforeEach(() => {
  installMemoryStorage();
});

describe("chat scroll memory", () => {
  it("returns null when a conversation has no remembered position", () => {
    expect(readChatScroll("session-a")).toBeNull();
  });

  it("keys the position by conversation", () => {
    expect(chatScrollKey("session-a")).toBe("vt.chat.scroll.session-a");

    writeChatScroll("session-a", 120);
    writeChatScroll("session-b", 40);

    expect(readChatScroll("session-a")).toBe(120);
    expect(readChatScroll("session-b")).toBe(40);
  });

  it("rounds the stored offset to whole pixels", () => {
    writeChatScroll("session-a", 120.6);

    expect(readChatScroll("session-a")).toBe(121);
    expect(
      JSON.parse(window.localStorage.getItem(chatScrollKey("session-a")) ?? "{}"),
    ).toEqual({ top: 121 });
  });

  it("ignores invalid stored values", () => {
    for (const value of ["", "abc", "-5", "NaN", "Infinity", "120"]) {
      window.localStorage.setItem(chatScrollKey("session-a"), value);
      expect(readChatScroll("session-a")).toBeNull();
    }
  });

  it("does not throw when storage is unavailable", () => {
    const storage = installMemoryStorage();
    storage.getItem = () => {
      throw new Error("storage unavailable");
    };
    expect(readChatScroll("session-a")).toBeNull();

    storage.setItem = () => {
      throw new Error("quota exceeded");
    };
    expect(() => writeChatScroll("session-a", 120)).not.toThrow();
  });
});
