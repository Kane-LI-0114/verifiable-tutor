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

/** The canonical phase order; only steps that actually exist are rendered. */
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
  summary,
  policy,
}: {
  summary: string;
  policy: PolicyState;
}) {
  const t = useT();
  return (
    <TraceLine>
      <BrainIcon className="size-4 shrink-0" />
      <TraceTitle>{t.chat.workChain}</TraceTitle>
      <TraceDescription>{summary}</TraceDescription>
      <Badge variant="secondary">{t.chat.policyStates[policy]}</Badge>
    </TraceLine>
  );
}

function ReasoningBlock({ text }: { text: string }) {
  const t = useT();
  return (
    <div className="space-y-1">
      <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
        <BrainIcon className="size-3" />
        {t.chat.reasoning}
      </p>
      <p className="max-h-64 overflow-auto whitespace-pre-wrap text-sm text-muted-foreground">
        {text}
      </p>
    </div>
  );
}

function WorkChainEventView({
  event,
  index,
}: {
  event: WorkChainEvent;
  index: number;
}) {
  if (event.kind === "reasoning") {
    if (!event.reasoning) {
      return null;
    }
    return <ReasoningBlock text={event.reasoning} />;
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
}

function EventList({ events }: { events: WorkChainEvent[] }) {
  return (
    <div className="space-y-3">
      {events.map((event, index) => (
        <WorkChainEventView
          key={`${event.kind}:${event.tool_call?.tool_call_id ?? index}`}
          event={event}
          index={index}
        />
      ))}
    </div>
  );
}

/**
 * Every step name that actually exists renders once, even without events.
 * Rows with the same name are merged so a repeated phase keeps one section,
 * and events from all of its step ids stay in their original order.
 */
function mergeStepRows(rows: WorkStep[]): WorkStep {
  const ordered = [...rows].sort(
    (left, right) => (left.position ?? 0) - (right.position ?? 0),
  );
  const base = ordered[0];
  const status = ordered.some((row) => row.status === "failed")
    ? "failed"
    : ordered.some((row) => row.status === "started")
      ? "started"
      : ordered.every((row) => row.status === "done")
        ? "done"
        : base.status;
  const durations = ordered
    .map((row) => row.duration_ms)
    .filter((value): value is number => value !== undefined);
  const detail = ordered.find((row) => row.detail)?.detail;
  const policy = ordered.find((row) => row.policy)?.policy;
  const rule_id = ordered.find((row) => row.rule_id)?.rule_id;
  return {
    ...base,
    status,
    detail,
    policy,
    rule_id,
    duration_ms:
      durations.length > 0
        ? durations.reduce((total, value) => total + value, 0)
        : undefined,
  };
}

function WorkChainSections({
  steps,
  events,
}: {
  steps: WorkStep[];
  events: WorkChainEvent[];
}) {
  const t = useT();
  const stepNameById = new Map(steps.map((step) => [step.id, step.step]));
  const rowsByName = new Map<WorkStepName, WorkStep[]>();
  for (const step of steps) {
    const rows = rowsByName.get(step.step) ?? [];
    rows.push(step);
    rowsByName.set(step.step, rows);
  }
  const merged = new Map(
    [...rowsByName.entries()].map(([name, rows]) => [name, mergeStepRows(rows)]),
  );
  const eventsByName = new Map<WorkStepName, WorkChainEvent[]>();
  const unstepped: WorkChainEvent[] = [];
  for (const event of events) {
    const name = event.step_id
      ? stepNameById.get(event.step_id)
      : undefined;
    if (name) {
      const list = eventsByName.get(name) ?? [];
      list.push(event);
      eventsByName.set(name, list);
    } else {
      unstepped.push(event);
    }
  }
  const ordered = [...merged.values()].sort(
    (left, right) => STEP_ORDER.indexOf(left.step) - STEP_ORDER.indexOf(right.step),
  );

  return (
    <div className="space-y-4">
      {ordered.map((step) => {
        const title = stepTitle(step, t);
        const stepEvents = eventsByName.get(step.step) ?? [];
        const showBody = step.detail !== undefined || stepEvents.length > 0;
        return (
          <section key={step.step} aria-label={title} className="min-w-0">
            <div
              className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-foreground"
              title={title}
            >
              <StatusIcon status={step.status} />
              <span className="font-medium">{t.chat.steps[step.step]}</span>
              {step.duration_ms !== undefined ? (
                <TraceDescription>{step.duration_ms} ms</TraceDescription>
              ) : null}
            </div>
            {showBody ? (
              <div className="mt-2 space-y-3 border-l pl-4">
                {step.detail ? (
                  <p className="text-sm text-muted-foreground">{step.detail}</p>
                ) : null}
                {stepEvents.length > 0 ? <EventList events={stepEvents} /> : null}
              </div>
            ) : null}
          </section>
        );
      })}
      {unstepped.length > 0 ? (
        <div className="space-y-3" aria-label={t.chat.workChain}>
          <EventList events={unstepped} />
        </div>
      ) : null}
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
  const uniqueSteps = [
    ...new Map(steps.map((step) => [step.step, step])).values(),
  ];
  const done = uniqueSteps.filter((step) => step.status === "done").length;
  const toolCallCount = events.filter((event) => event.kind === "tool_call").length;
  const summary =
    uniqueSteps.length > 0
      ? format(t.chat.workChainSummary, { done, total: uniqueSteps.length })
      : format(t.chat.toolCallsSummary, { count: toolCallCount });
  const hasContent = steps.length > 0 || events.length > 0;

  return (
    <Trace role="group" aria-label={t.a11y.workChain}>
      <TraceCollapsible>
        <TraceCollapsibleTrigger>
          <WorkChainHeader summary={summary} policy={policy} />
        </TraceCollapsibleTrigger>
        <TraceCollapsibleContent>
          {hasContent ? (
            <WorkChainSections steps={steps} events={events} />
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
