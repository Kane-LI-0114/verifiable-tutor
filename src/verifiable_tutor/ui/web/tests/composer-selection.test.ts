import { beforeEach, describe, expect, it } from "vitest";

import {
  COMPOSER_SELECTION_KEY,
  DEFAULT_COMPOSER_SELECTION,
  readComposerSelection,
  saveComposerSelection,
} from "@/lib/chat/composer-selection";

import { installMemoryStorage } from "./memory-storage";

beforeEach(() => {
  installMemoryStorage();
});

describe("composer selection storage", () => {
  it("returns the defaults when nothing is stored", () => {
    expect(readComposerSelection()).toEqual(DEFAULT_COMPOSER_SELECTION);
  });

  it("round-trips a chosen model and thinking level", () => {
    saveComposerSelection({ model: "mimo-pro", thinking: "on" });

    expect(readComposerSelection()).toEqual({
      model: "mimo-pro",
      thinking: "on",
    });
    expect(window.localStorage.getItem(COMPOSER_SELECTION_KEY)).toContain(
      "mimo-pro",
    );
  });

  it("clamps a MiMo selection to off or on", () => {
    saveComposerSelection({ model: "mimo-flash", thinking: "max" });

    expect(readComposerSelection()).toEqual({
      model: "mimo-flash",
      thinking: "on",
    });
    expect(window.localStorage.getItem(COMPOSER_SELECTION_KEY)).toContain(
      '"thinking":"on"',
    );

    window.localStorage.setItem(
      COMPOSER_SELECTION_KEY,
      JSON.stringify({ model: "mimo-pro", thinking: "low" }),
    );
    expect(readComposerSelection()).toEqual({
      model: "mimo-pro",
      thinking: "on",
    });
  });

  it("falls back field by field for unknown stored values", () => {
    window.localStorage.setItem(
      COMPOSER_SELECTION_KEY,
      JSON.stringify({ model: "gpt-4", thinking: "high" }),
    );

    expect(readComposerSelection()).toEqual({
      model: DEFAULT_COMPOSER_SELECTION.model,
      thinking: "high",
    });
  });

  it("falls back when the stored value is not usable JSON", () => {
    window.localStorage.setItem(COMPOSER_SELECTION_KEY, "not-json");
    expect(readComposerSelection()).toEqual(DEFAULT_COMPOSER_SELECTION);

    window.localStorage.setItem(COMPOSER_SELECTION_KEY, "null");
    expect(readComposerSelection()).toEqual(DEFAULT_COMPOSER_SELECTION);

    window.localStorage.setItem(COMPOSER_SELECTION_KEY, "[]");
    expect(readComposerSelection()).toEqual(DEFAULT_COMPOSER_SELECTION);
  });

  it("keeps working when storage refuses reads and writes", () => {
    const storage = installMemoryStorage();
    storage.getItem = () => {
      throw new Error("storage unavailable");
    };
    expect(readComposerSelection()).toEqual(DEFAULT_COMPOSER_SELECTION);

    storage.setItem = () => {
      throw new Error("quota exceeded");
    };
    expect(() =>
      saveComposerSelection({ model: "mimo-flash", thinking: "max" }),
    ).not.toThrow();
  });
});
