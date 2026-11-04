import type { UIMessage } from "ai";

import type {
  ChatMessage,
  ConversationTurn,
  PolicyState,
  WorkStep,
  WorkStepName,
  WorkStepStatus,
} from "@/lib/types";

/** Payload of the backend `data-step` frame, rendered by the work chain. */
export interface WorkStepData {
  step: WorkStepName;
  status: WorkStepStatus;
  detail?: string;
  duration_ms?: number;
  policy?: PolicyState;
  rule_id?: string;
}

/** The model provider and tier that produced an answer. */
export interface ModelProviderTier {
  provider: string | null;
  tier: string | null;
}

/** Provider and tier travel with a persisted message; streamed turns fill them in. */
export type MessageMetadata = ModelProviderTier;

export type TutorDataParts = { step: WorkStepData } & Record<string, unknown>;

export type TutorUIMessage = UIMessage<MessageMetadata, TutorDataParts>;

export type TutorPart = TutorUIMessage["parts"][number];

/** Stored history becomes UI messages with plain text parts. */
export function toTutorMessages(messages: ChatMessage[]): TutorUIMessage[] {
  return messages.map((message) => ({
    id: message.id,
    role: message.role,
    metadata: { provider: message.provider, tier: message.tier },
    parts: message.content.length > 0 ? [{ type: "text", text: message.content }] : [],
  }));
}

function partText(part: TutorPart): string {
  if (part.type === "text") {
    return part.text;
  }
  return "";
}

function workSteps(parts: TutorPart[]): WorkStep[] {
  const steps: WorkStep[] = [];
  const index = new Map<WorkStepName, number>();
  for (const part of parts) {
    if (part.type !== "data-step") {
      continue;
    }
    const data = part.data as WorkStepData;
    const existing = index.get(data.step);
    const step: WorkStep = {
      step: data.step,
      status: data.status,
      detail: data.detail,
      duration_ms: data.duration_ms,
      policy: data.policy,
      rule_id: data.rule_id,
    };
    if (existing === undefined) {
      index.set(data.step, steps.length);
      steps.push(step);
    } else {
      steps[existing] = step;
    }
  }
  return steps;
}

function reasoningText(parts: TutorPart[]): string {
  return parts
    .filter((part) => part.type === "reasoning")
    .map((part) => part.text)
    .join("");
}

/**
 * Turn a UI message into the shape the chat components already render.
 *
 * Work steps and reasoning are stream-only for now: the backend persists the
 * answer text but not the turn trace, so a reloaded history message has none.
 */
export function toConversationTurn(
  message: TutorUIMessage,
  sequence: number,
): ConversationTurn {
  const role = message.role === "user" ? "user" : "assistant";
  const content = message.parts.map(partText).join("");
  const metadata = message.metadata ?? { provider: null, tier: null };
  const turn: ConversationTurn = {
    message: {
      id: message.id,
      sequence,
      role,
      content,
      provider: metadata.provider ?? null,
      tier: metadata.tier ?? null,
      created_at: "",
    },
  };
  if (role === "assistant") {
    const steps = workSteps(message.parts);
    const reasoning = reasoningText(message.parts);
    if (steps.length > 0 || reasoning.length > 0) {
      turn.meta = {
        work_steps: steps,
        reasoning,
        citations: [],
        tool_calls: [],
        policy_state: steps.find((step) => step.policy)?.policy ?? "active",
      };
    }
  }
  return turn;
}

export function toConversationTurns(
  messages: TutorUIMessage[],
): ConversationTurn[] {
  return messages.map((message, index) =>
    toConversationTurn(message, index + 1),
  );
}

export function lastUserText(messages: TutorUIMessage[]): string {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role !== "user") {
      continue;
    }
    return message.parts.map(partText).join("").trim();
  }
  return "";
}
