import {
  MODEL_OPTIONS,
  THINKING_LEVELS,
  type ModelId,
  type ThinkingLevel,
} from "@/lib/models";

/** Browser storage key for the composer's last model and thinking choice. */
export const COMPOSER_SELECTION_KEY = "vt.composer.selection";

export interface ComposerSelection {
  model: ModelId;
  thinking: ThinkingLevel;
}

/** The selection a fresh browser starts from; also the fallback for bad data. */
export const DEFAULT_COMPOSER_SELECTION: ComposerSelection = {
  model: "deepseek-flash",
  thinking: "off",
};

function isModelId(value: unknown): value is ModelId {
  return (
    typeof value === "string" &&
    MODEL_OPTIONS.some((option) => option.id === value)
  );
}

function isThinkingLevel(value: unknown): value is ThinkingLevel {
  return (
    typeof value === "string" &&
    (THINKING_LEVELS as readonly string[]).includes(value)
  );
}

/**
 * Read the composer selection the browser last stored.
 *
 * The value is a user preference, not conversation data: a refresh or another
 * conversation keeps it. Missing, unreadable, or invalid values fall back to
 * the defaults so a stale or corrupted entry never breaks the composer.
 */
export function readComposerSelection(): ComposerSelection {
  try {
    const raw =
      typeof window === "undefined"
        ? null
        : window.localStorage?.getItem(COMPOSER_SELECTION_KEY);
    if (!raw) {
      return DEFAULT_COMPOSER_SELECTION;
    }
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) {
      return DEFAULT_COMPOSER_SELECTION;
    }
    const { model, thinking } = parsed as Record<string, unknown>;
    return {
      model: isModelId(model) ? model : DEFAULT_COMPOSER_SELECTION.model,
      thinking: isThinkingLevel(thinking)
        ? thinking
        : DEFAULT_COMPOSER_SELECTION.thinking,
    };
  } catch {
    return DEFAULT_COMPOSER_SELECTION;
  }
}

/** Store the composer selection; unavailable storage silently keeps defaults. */
export function saveComposerSelection(selection: ComposerSelection): void {
  try {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage?.setItem(
      COMPOSER_SELECTION_KEY,
      JSON.stringify(selection),
    );
  } catch {
    // Private mode or quota refusal: the in-memory selection still works.
  }
}
