import {
  BadgeCheckIcon,
  BrainIcon,
  CheckCircle2Icon,
  CircleDashedIcon,
  Loader2Icon,
  PenLineIcon,
  QuoteIcon,
  ScaleIcon,
  SearchIcon,
  XCircleIcon,
} from "lucide-react";
import type { ComponentType } from "react";

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

const STEP_ICONS: Record<
  WorkStepName,
  ComponentType<{ className?: string }>
> = {
  understand: BrainIcon,
  retrieve: SearchIcon,
  verify: BadgeCheckIcon,
  decide: ScaleIcon,
  generate: PenLineIcon,
  cite: QuoteIcon,
};

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
    return <CheckCircle2Icon className="size-3.5 text-muted-foreground" />;
  }
  if (status === "started") {
    return <Loader2Icon className="size-3.5 animate-spin" />;
  }
  if (status === "failed") {
    return <XCircleIcon className="size-3.5 text-destructive" />;
  }
  return <CircleDashedIcon className="size-3.5 opacity-60" />;
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

/** Compact phase summary; details live in the chip title, not a second list. */
function StepChips({ steps }: { steps: WorkStep[] }) {
  const t = useT();
  if (steps.length === 0) {
    return null;
  }
  const ordered = [...steps].sort(
    (left, right) => STEP_ORDER.indexOf(left.step) - STEP_ORDER.indexOf(right.step),
  );
  return (
    <div className="flex flex-wrap gap-1.5 pl-6">
      {ordered.map((step) => {
        const Icon = STEP_ICONS[step.step];
        const title = stepTitle(step, t);
        return (
          <Badge
            key={step.step}
            variant={step.status === "failed" ? "destructive" : "outline"}
            className="gap-1 font-normal"
            title={title}
            aria-label={title}
          >
            <StatusIcon status={step.status} />
            <Icon className="size-3" />
            {t.chat.steps[step.step]}
          </Badge>
        );
      })}
    </div>
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

  const header = <WorkChainHeader summary={summary} policy={policy} />;
  const chips = <StepChips steps={steps} />;

  return (
    <Trace role="group" aria-label={t.a11y.workChain}>
      <TraceCollapsible>
        <TraceCollapsibleTrigger>{header}</TraceCollapsibleTrigger>
        {chips}
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
