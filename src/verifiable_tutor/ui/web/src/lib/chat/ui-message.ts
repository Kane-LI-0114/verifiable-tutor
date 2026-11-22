import type { UIMessage } from "ai";

import type {
  AssistantMeta,
  ChatMessage,
  CitationSource,
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
  id?: string;
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
  step_id?: string;
}

export interface SourcesData {
  sources: CitationSource[];
}

export type TutorDataParts = {
  step: WorkStepData;
  tool: ToolCallData;
  sources: SourcesData;
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
  const index = new Map<string, number>();
  for (const part of parts) {
    if (part.type !== "data-step") {
      continue;
    }
    const data = part.data as WorkStepData;
    const id = data.id ?? data.step;
    const existing = index.get(id);
    const step: WorkStep = {
      id,
      step: data.step,
      status: data.status,
      detail: data.detail,
      duration_ms: data.duration_ms,
      policy: data.policy,
      rule_id: data.rule_id,
    };
    if (existing === undefined) {
      index.set(id, steps.length);
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
  let generateStepId: string | undefined;
  let currentStepId: string | undefined;
  let reasoning = "";
  let reasoningStepId: string | undefined;
  const flushReasoning = () => {
    if (reasoning.trim().length === 0) {
      return;
    }
    events.push({ kind: "reasoning", reasoning, step_id: reasoningStepId });
    reasoning = "";
  };
  for (const part of parts) {
    if (part.type === "step-start") {
      currentStepId = generateStepId;
      continue;
    }
    if (part.type === "data-step") {
      const data = part.data as WorkStepData;
      const id = data.id ?? data.step;
      if (data.step === "generate") {
        generateStepId = id;
      }
      if (data.status === "started") {
        currentStepId = id;
      } else if (currentStepId === id) {
        currentStepId = generateStepId;
      }
      continue;
    }
    if (part.type === "reasoning") {
      if (reasoning.length === 0) {
        reasoningStepId = currentStepId;
      }
      reasoning += part.text;
      continue;
    }
    if (part.type !== "data-tool") {
      continue;
    }
    const data = part.data as ToolCallData;
    flushReasoning();
    const stepId = data.step_id ?? currentStepId;
    const key = data.tool_call_id ?? `${data.name}:${events.length}`;
    const call = toToolCall(data);
    const existing = toolIndex.get(key);
    if (existing === undefined) {
      toolIndex.set(key, events.length);
      events.push({ kind: "tool_call", tool_call: call, step_id: stepId });
    } else {
      events[existing] = { kind: "tool_call", tool_call: call, step_id: stepId };
    }
  }
  flushReasoning();
  return alignReasoningSteps(events);
}

/**
 * A reasoning segment belongs with the tool calls it produced. Walk backward so
 * the last reasoning block before a tool adopts that tool's step; final
 * reasoning with no later tool stays on generate. This also repairs turns
 * stored before the backend attached reasoning to the tool step.
 */
export function alignReasoningSteps(
  events: WorkChainEvent[],
): WorkChainEvent[] {
  const aligned = events.map((event) => ({ ...event }));
  let nextToolStepId: string | undefined;
  for (let index = aligned.length - 1; index >= 0; index -= 1) {
    const event = aligned[index];
    if (event.kind === "tool_call") {
      nextToolStepId = event.step_id ?? nextToolStepId;
    } else if (nextToolStepId !== undefined) {
      aligned[index] = { ...event, step_id: nextToolStepId };
    }
  }
  return aligned;
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

/** The latest full source snapshot the backend streamed for this turn. */
function sourcesFromParts(parts: TutorPart[]): CitationSource[] {
  for (let index = parts.length - 1; index >= 0; index -= 1) {
    const part = parts[index];
    if (part.type !== "data-sources") {
      continue;
    }
    const data = part.data as SourcesData;
    if (Array.isArray(data.sources)) {
      return data.sources;
    }
  }
  return [];
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
    (stored.sources ?? []).length === 0 &&
    stored.tool_calls.length === 0 &&
    events.length === 0
  ) {
    return undefined;
  }
  return {
    work_steps: stored.work_steps,
    reasoning,
    citations: stored.citations,
    sources: stored.sources ?? [],
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
      sources: stored?.sources ?? [],
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
      const sources = sourcesFromParts(message.parts);
      if (steps.length > 0 || events.length > 0 || sources.length > 0) {
        turn.meta = {
          work_steps: steps,
          reasoning,
          citations: [],
          sources,
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
