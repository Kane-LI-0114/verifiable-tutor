export const MODEL_OPTIONS = [
  { id: "deepseek-flash", provider: "deepseek", tier: "flash" },
  { id: "mimo-flash", provider: "mimo", tier: "flash" },
  { id: "mimo-pro", provider: "mimo", tier: "pro" },
] as const;

export type ModelId = (typeof MODEL_OPTIONS)[number]["id"];

export const THINKING_LEVELS = ["off", "low", "high", "max", "on"] as const;

export type ThinkingLevel = (typeof THINKING_LEVELS)[number];

/** The thinking choices each model actually exposes in the composer. */
export const THINKING_LEVELS_BY_MODEL: Record<
  ModelId,
  readonly ThinkingLevel[]
> = {
  "deepseek-flash": ["off", "low", "high", "max"],
  // MiMo has only on and off; on is the enabled value it accepts.
  "mimo-flash": ["off", "on"],
  "mimo-pro": ["off", "on"],
};

export function thinkingLevelsFor(model: ModelId): readonly ThinkingLevel[] {
  return THINKING_LEVELS_BY_MODEL[model];
}

/** Clamp a level to the model's choices; a non-off request becomes on. */
export function normalizeThinkingLevel(
  model: ModelId,
  level: ThinkingLevel,
): ThinkingLevel {
  const levels = thinkingLevelsFor(model);
  if (levels.includes(level)) {
    return level;
  }
  if (level === "off") {
    return "off";
  }
  if (levels.includes("on")) {
    return "on";
  }
  if (levels.includes("high")) {
    return "high";
  }
  return levels[levels.length - 1];
}
