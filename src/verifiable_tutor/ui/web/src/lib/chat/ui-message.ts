import type { UIMessage } from "ai";

import type {
  AssistantMeta,
  ChatMessage,
  ConversationTurn,
  PolicyState,
  ToolCall,
  WorkChainEvent,
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

/** Payload of the backend `data-tool` frame, rendered by the tool trace. */
export interface ToolCallData {
  tool_call_id?: string;
  name: string;
  status: ToolCall["status"];
  arguments?: unknown;
  output?: string | null;
  result?: unknown;
  duration_ms?: number | null;
}

export type TutorDataParts = {
  step: WorkStepData;
  tool: ToolCallData;
} & Record<string, unknown>;

export type TutorUIMessage = UIMessage<MessageMetadata, TutorDataParts>;

export type TutorPart = TutorUIMessage["parts"][number];

/**
 * Stored history becomes UI messages with plain text parts. The persisted turn
 * metadata is not part of a UI message, so `toConversationTurns` applies it
 * from the same rows.
 */
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

export function toToolCall(data: ToolCallData): ToolCall {
  return {
    tool_call_id: data.tool_call_id,
    name: data.name,
    arguments: data.arguments,
    result: data.result,
    duration_ms: data.duration_ms ?? undefined,
    command: [],
    exit_code: null,
    output: typeof data.output === "string" ? data.output : "",
    status: data.status,
  };
}

function toolCalls(parts: TutorPart[]): ToolCall[] {
  const calls = new Map<string, ToolCall>();
  for (const part of parts) {
    if (part.type !== "data-tool") {
      continue;
    }
    const data = part.data as ToolCallData;
    const key = data.tool_call_id ?? `${data.name}:${calls.size}`;
    const existing = calls.get(key);
    if (existing && existing.status !== "running" && data.status === "running") {
      continue;
    }
    calls.set(key, toToolCall(data));
  }
  return [...calls.values()];
}

/** Build the ordered work chain from live frames: reasoning, then tool calls. */
function workChainEvents(parts: TutorPart[]): WorkChainEvent[] {
  const events: WorkChainEvent[] = [];
  const toolIndex = new Map<string, number>();
  let reasoning = "";
  const flushReasoning = () => {
    if (reasoning.trim().length === 0) {
      return;
    }
    events.push({ kind: "reasoning", reasoning });
    reasoning = "";
  };
  for (const part of parts) {
    if (part.type === "reasoning") {
      reasoning += part.text;
      continue;
    }
    if (part.type !== "data-tool") {
      continue;
    }
    const data = part.data as ToolCallData;
    flushReasoning();
    const key = data.tool_call_id ?? `${data.name}:${events.length}`;
    const call = toToolCall(data);
    const existing = toolIndex.get(key);
    if (existing === undefined) {
      toolIndex.set(key, events.length);
      events.push({ kind: "tool_call", tool_call: call });
    } else {
      events[existing] = { kind: "tool_call", tool_call: call };
    }
  }
  flushReasoning();
  return events;
}

function legacyEvents(reasoning: string, calls: ToolCall[]): WorkChainEvent[] {
  const events: WorkChainEvent[] = [];
  if (reasoning.length > 0) {
    events.push({ kind: "reasoning", reasoning });
  }
  for (const call of calls) {
    events.push({ kind: "tool_call", tool_call: call });
  }
  return events;
}

function reasoningText(parts: TutorPart[]): string {
  return parts
    .filter((part) => part.type === "reasoning")
    .map((part) => part.text)
    .join("");
}

/**
 * The turn metadata a stored assistant row carries. The first step that holds a
 * policy labels the work chain. A row with no metadata at all is a legacy
 * answer and yields no trace, so the thread does not show an empty work chain.
 */
function storedMeta(stored: ChatMessage): AssistantMeta | undefined {
  const reasoning = stored.reasoning ?? "";
  const storedEvents = stored.events ?? [];
  const events =
    storedEvents.length > 0
      ? storedEvents
      : legacyEvents(reasoning, stored.tool_calls);
  if (
    stored.work_steps.length === 0 &&
    reasoning.length === 0 &&
    stored.citations.length === 0 &&
    stored.tool_calls.length === 0 &&
    events.length === 0
  ) {
    return undefined;
  }
  return {
    work_steps: stored.work_steps,
    reasoning,
    citations: stored.citations,
    tool_calls: stored.tool_calls,
    events,
    policy_state:
      stored.work_steps.find((step) => step.policy)?.policy ?? "active",
  };
}

/**
 * Turn a UI message into the shape the chat components already render.
 *
 * A stored row supplies the turn metadata by message id, so a conversation
 * reloaded from the API keeps its work chain, reasoning, citations, and tool
 * calls. A message without a stored row (the live stream, and the replay
 * frames) derives the same metadata from its own parts instead.
 */
export function toConversationTurn(
  message: TutorUIMessage,
  sequence: number,
  stored?: ChatMessage,
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
      reasoning: stored?.reasoning ?? null,
      model: stored?.model ?? null,
      thinking: stored?.thinking ?? null,
      work_steps: stored?.work_steps ?? [],
      citations: stored?.citations ?? [],
      tool_calls: stored?.tool_calls ?? [],
      events: stored?.events ?? [],
    },
  };
  if (role === "assistant") {
    if (stored !== undefined) {
      const meta = storedMeta(stored);
      if (meta !== undefined) {
        turn.meta = meta;
      }
    } else {
      const steps = workSteps(message.parts);
      const reasoning = reasoningText(message.parts);
      const calls = toolCalls(message.parts);
      const events = workChainEvents(message.parts);
      if (steps.length > 0 || events.length > 0) {
        turn.meta = {
          work_steps: steps,
          reasoning,
          citations: [],
          tool_calls: calls,
          events,
          policy_state: steps.find((step) => step.policy)?.policy ?? "active",
        };
      }
    }
  }
  return turn;
}

export function toConversationTurns(
  messages: TutorUIMessage[],
  storedMessages: ChatMessage[] = [],
): ConversationTurn[] {
  const storedById = new Map(
    storedMessages.map((message) => [message.id, message]),
  );
  return messages.map((message, index) =>
    toConversationTurn(message, index + 1, storedById.get(message.id)),
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
