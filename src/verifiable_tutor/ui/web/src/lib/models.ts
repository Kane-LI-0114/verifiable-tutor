export const MODEL_OPTIONS = [
  { id: "deepseek-flash", provider: "deepseek", tier: "flash" },
  { id: "mimo-flash", provider: "mimo", tier: "flash" },
  { id: "mimo-pro", provider: "mimo", tier: "pro" },
] as const;

export type ModelId = (typeof MODEL_OPTIONS)[number]["id"];

export const THINKING_LEVELS = ["off", "low", "high", "max"] as const;

export type ThinkingLevel = (typeof THINKING_LEVELS)[number];
