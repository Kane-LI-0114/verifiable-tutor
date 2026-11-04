import { useCallback, useEffect, useState } from "react";

import { sessionsApi } from "@/lib/api/sessions";
import { useSession } from "@/lib/auth/session";
import type { Messages } from "@/lib/i18n/en";
import type { AssistantMeta, ConversationTurn } from "@/lib/types";

import { toChunkStream } from "./stream";
import type { WorkStepData } from "./ui-message";

export type ReplayStatus = "loading" | "streaming" | "done" | "error";

export interface ReplayState {
  status: ReplayStatus;
  turns: ConversationTurn[];
  errorDescription: string | null;
  /** Re-fetch the recorded stream (used by the error retry action). */
  retry: () => void;
}

interface ReplayFrame {
  type: string;
  messageId?: string;
  delta?: string;
  data?: WorkStepData;
  errorText?: string;
}

function emptyMeta(): AssistantMeta {
  return {
    work_steps: [],
    reasoning: "",
    citations: [],
    tool_calls: [],
    policy_state: "active",
  };
}

function emptyAssistant(sequence: number): ConversationTurn {
  return {
    message: {
      id: `replay-assistant-${sequence}`,
      sequence,
      role: "assistant",
      content: "",
      provider: null,
      tier: null,
      created_at: "",
    },
    meta: emptyMeta(),
  };
}

/**
 * Turn stored history into replay placeholders: user turns keep their text and
 * assistant turns start empty so only the recorded frames fill them.
 */
export function replayPlaceholders(history: ConversationTurn[]): ConversationTurn[] {
  return history.map((turn) => {
    if (turn.message.role === "user") {
      return turn;
    }
    const placeholder = emptyAssistant(turn.message.sequence);
    return {
      ...placeholder,
      message: {
        ...placeholder.message,
        id: turn.message.id,
        provider: turn.message.provider,
        tier: turn.message.tier,
      },
    };
  });
}

type ReplayData = Omit<ReplayState, "retry">;

function applyFrame(
  state: ReplayData,
  frame: ReplayFrame,
  assistantIndices: number[],
  cursorRef: { current: number },
): ReplayData {
  if (frame.type === "start") {
    const nextCursor = cursorRef.current + 1;
    cursorRef.current = nextCursor;
    const turns = [...state.turns];
    if (assistantIndices.length <= nextCursor) {
      turns.push(emptyAssistant(turns.length + 1));
      assistantIndices.push(turns.length - 1);
    }
    return { ...state, turns };
  }

  const index = assistantIndices[cursorRef.current];
  const target = index === undefined ? undefined : state.turns[index];
  if (target === undefined) {
    return state;
  }
  const turns = state.turns.map((turn, position) =>
    position === index
      ? { ...turn, meta: { ...(turn.meta ?? emptyMeta()) } }
      : turn,
  );
  const turn = turns[index];
  const meta = turn.meta ?? emptyMeta();
  turn.meta = meta;

  if (frame.type === "text-delta") {
    turn.message = { ...turn.message, content: turn.message.content + (frame.delta ?? "") };
  } else if (frame.type === "reasoning-delta") {
    meta.reasoning = (meta.reasoning ?? "") + (frame.delta ?? "");
  } else if (frame.type === "data-step" && frame.data) {
    const data = frame.data;
    const steps = meta.work_steps.filter((step) => step.step !== data.step);
    steps.push({
      step: data.step,
      status: data.status,
      detail: data.detail,
      duration_ms: data.duration_ms,
      policy: data.policy,
      rule_id: data.rule_id,
    });
    meta.work_steps = steps;
  } else if (frame.type === "error") {
    turn.message = { ...turn.message, content: "" };
    return { ...state, turns, status: "error" };
  }
  return { ...state, turns };
}

/**
 * Stream a recorded session trace through the replay endpoint.
 *
 * Uses the same UI message stream parser as live chat, but a small reducer
 * instead of `useChat`: replay has no request body and no user message to add.
 */
export function useReplayStream({
  sessionId,
  speed,
  historyTurns,
  t,
}: {
  sessionId: string;
  speed: string;
  historyTurns: ConversationTurn[];
  t: Messages;
}): ReplayState {
  const { expire } = useSession();
  const [state, setState] = useState<ReplayData>(() => ({
    status: "loading",
    turns: replayPlaceholders(historyTurns),
    errorDescription: null,
  }));
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => {
    setAttempt((current) => current + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    let current: ReplayData = {
      status: "loading",
      turns: replayPlaceholders(historyTurns),
      errorDescription: null,
    };
    const assistantIndices = historyTurns
      .map((turn, index) => (turn.message.role === "assistant" ? index : -1))
      .filter((index) => index >= 0);
    const cursor = { current: -1 };
    setState(current);

    function fail() {
      current = {
        ...current,
        status: "error",
        errorDescription: t.chat.replayErrorBody,
      };
      if (!cancelled) {
        setState(current);
      }
    }

    async function run() {
      let response: Response;
      try {
        response = await fetch(sessionsApi.replayUrl(sessionId, speed), {
          credentials: "same-origin",
          signal: controller.signal,
        });
      } catch {
        fail();
        return;
      }
      if (!response.ok) {
        if (response.status === 401) {
          // The session expired: clear it so the guards send the reader to
          // sign-in instead of showing a replay failure with a dead retry.
          if (!cancelled) {
            expire();
          }
          return;
        }
        fail();
        return;
      }
      if (response.body === null) {
        return;
      }
      const chunks = toChunkStream(response.body);

      current = { ...current, status: "streaming" };
      if (!cancelled) {
        setState(current);
      }

      try {
        for await (const chunk of chunks) {
          if (cancelled) {
            return;
          }
          // Apply frames outside the state updater: React can double-invoke an
          // updater under StrictMode, and the reducer advances the replay cursor.
          current = applyFrame(current, chunk as ReplayFrame, assistantIndices, cursor);
          if (!cancelled) {
            setState(current);
          }
        }
        if (!cancelled) {
          current = current.status === "error" ? current : { ...current, status: "done" };
          setState(current);
        }
      } catch {
        fail();
      }
    }

    void run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [attempt, expire, historyTurns, sessionId, speed, t]);

  return { ...state, retry };
}
