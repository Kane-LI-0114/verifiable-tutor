import {
  BrainIcon,
  CheckCircle2Icon,
  CircleDashedIcon,
  Loader2Icon,
  XCircleIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ToolCallTrace } from "@/components/chat/tool-call";
import {
  Trace,
  TraceCollapsible,
  TraceCollapsibleContent,
  TraceCollapsibleTrigger,
  TraceDescription,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import { format, useT } from "@/lib/i18n";
import type {
  PolicyState,
  WorkChainEvent,
  WorkStep,
  WorkStepName,
} from "@/lib/types";

/** The canonical phase order, independent of the order the steps were written. */
const STEP_ORDER: WorkStepName[] = [
  "understand",
  "retrieve",
  "verify",
  "decide",
  "generate",
  "cite",
];

function StatusIcon({ status }: { status: WorkStep["status"] }) {
  if (status === "done") {
    return <CheckCircle2Icon className="size-3 text-muted-foreground" />;
  }
  if (status === "started") {
    return <Loader2Icon className="size-3 animate-spin" />;
  }
  if (status === "failed") {
    return <XCircleIcon className="size-3 text-destructive" />;
  }
  return <CircleDashedIcon className="size-3 opacity-60" />;
}

function stepTitle(step: WorkStep, t: ReturnType<typeof useT>): string {
  const parts = [t.chat.steps[step.step]];
  if (step.duration_ms !== undefined) {
    parts.push(`${step.duration_ms} ms`);
  }
  if (step.detail) {
    parts.push(step.detail);
  }
  if (step.policy) {
    parts.push(t.chat.policyStates[step.policy]);
  }
  if (step.rule_id) {
    parts.push(`${t.chat.rule}: ${step.rule_id}`);
  }
  return parts.join(" · ");
}

function WorkChainHeader({
  steps,
  summary,
  policy,
}: {
  steps: WorkStep[];
  summary: string;
  policy: PolicyState;
}) {
  const t = useT();
  return (
    <TraceLine>
      <BrainIcon className="size-4 shrink-0" />
      <TraceTitle>{t.chat.workChain}</TraceTitle>
      <TraceDescription>{summary}</TraceDescription>
      <StepRail steps={steps} />
      <Badge variant="secondary">{t.chat.policyStates[policy]}</Badge>
    </TraceLine>
  );
}

/** Inline phase rail: one node per phase, status and details in the tooltip. */
function StepRail({ steps }: { steps: WorkStep[] }) {
  const t = useT();
  if (steps.length === 0) {
    return null;
  }
  const ordered = [...steps].sort(
    (left, right) => STEP_ORDER.indexOf(left.step) - STEP_ORDER.indexOf(right.step),
  );
  return (
    <span className="hidden shrink-0 items-center gap-1 sm:flex">
      {ordered.map((step, index) => {
        const title = stepTitle(step, t);
        const statusClass =
          step.status === "failed"
            ? "border-destructive/40 text-destructive"
            : step.status === "started"
              ? "border-primary/40 text-primary"
              : step.status === "done"
                ? "border-border bg-muted/60 text-muted-foreground"
                : "border-border text-muted-foreground/50";
        return (
          <span key={step.step} className="flex items-center gap-1">
            {index > 0 ? (
              <span className="h-px w-2 bg-border" aria-hidden="true" />
            ) : null}
            <span
              role="img"
              aria-label={title}
              title={title}
              className={`flex size-4 shrink-0 items-center justify-center rounded-full border ${statusClass}`}
            >
              <StatusIcon status={step.status} />
            </span>
          </span>
        );
      })}
    </span>
  );
}

/** The ordered execution timeline: reasoning segments and tool calls. */
function WorkChainEvents({ events }: { events: WorkChainEvent[] }) {
  const t = useT();
  return (
    <div className="space-y-3">
      {events.map((event, index) => {
        if (event.kind === "reasoning") {
          if (!event.reasoning) {
            return null;
          }
          return (
            <div key={`reasoning:${index}`} className="space-y-1">
              <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                <BrainIcon className="size-3" />
                {t.chat.reasoning}
              </p>
              <p className="max-h-64 overflow-auto whitespace-pre-wrap text-sm text-muted-foreground">
                {event.reasoning}
              </p>
            </div>
          );
        }
        if (!event.tool_call) {
          return null;
        }
        return (
          <ToolCallTrace
            key={event.tool_call.tool_call_id ?? `tool:${index}`}
            call={event.tool_call}
          />
        );
      })}
    </div>
  );
}

export function WorkChain({
  steps,
  policy,
  events,
}: {
  steps: WorkStep[];
  policy: PolicyState;
  events: WorkChainEvent[];
}) {
  const t = useT();
  const done = steps.filter((step) => step.status === "done").length;
  const toolCallCount = events.filter((event) => event.kind === "tool_call").length;
  const summary =
    steps.length > 0
      ? format(t.chat.workChainSummary, { done, total: steps.length })
      : format(t.chat.toolCallsSummary, { count: toolCallCount });

  const header = (
    <WorkChainHeader steps={steps} summary={summary} policy={policy} />
  );

  return (
    <Trace role="group" aria-label={t.a11y.workChain}>
      <TraceCollapsible>
        <TraceCollapsibleTrigger>{header}</TraceCollapsibleTrigger>
        <TraceCollapsibleContent>
          {events.length > 0 ? (
            <WorkChainEvents events={events} />
          ) : (
            <p className="text-xs text-muted-foreground">
              {t.chat.noWorkChainEvents}
            </p>
          )}
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>
  );
}
