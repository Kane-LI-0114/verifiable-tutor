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
  TerminalIcon,
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
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import { format, useT } from "@/lib/i18n";
import type { PolicyState, ToolCall, WorkStep, WorkStepName } from "@/lib/types";

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

function lineStatus(status: WorkStep["status"]) {
  if (status === "started") {
    return "running" as const;
  }
  if (status === "failed") {
    return "error" as const;
  }
  if (status === "pending") {
    return "pending" as const;
  }
  return undefined;
}

export function WorkChain({
  steps,
  policy,
  toolCalls,
}: {
  steps: WorkStep[];
  policy: PolicyState;
  toolCalls: ToolCall[];
}) {
  const t = useT();
  const done = steps.filter((step) => step.status === "done").length;
  const summary =
    steps.length > 0
      ? format(t.chat.workChainSummary, { done, total: steps.length })
      : format(t.chat.toolCallsSummary, { count: toolCalls.length });

  return (
    <Trace role="group" aria-label={t.a11y.workChain}>
      <TraceCollapsible>
        <TraceCollapsibleTrigger>
          <TraceLine>
            <TraceIcon>
              <BrainIcon />
            </TraceIcon>
            <TraceTitle>{t.chat.workChain}</TraceTitle>
            <TraceDescription>{summary}</TraceDescription>
            <Badge variant="secondary">{t.chat.policyStates[policy]}</Badge>
          </TraceLine>
        </TraceCollapsibleTrigger>
        <TraceCollapsibleContent>
          <ul className="space-y-2">
            {steps.map((step) => {
              const Icon = STEP_ICONS[step.step];
              return (
                <li key={step.step} className="space-y-0.5">
                  <TraceLine status={lineStatus(step.status)}>
                    <TraceIcon>
                      <StatusIcon status={step.status} />
                    </TraceIcon>
                    <TraceTitle>{t.chat.steps[step.step]}</TraceTitle>
                    {step.duration_ms === undefined ? null : (
                      <TraceDescription>{step.duration_ms} ms</TraceDescription>
                    )}
                    {step.policy ? (
                      <Badge variant="outline">
                        {t.chat.policyStates[step.policy]}
                      </Badge>
                    ) : null}
                  </TraceLine>
                  <div className="pl-6">
                    {step.detail ? (
                      <p className="text-xs text-muted-foreground">{step.detail}</p>
                    ) : null}
                    {step.rule_id ? (
                      <p className="font-mono text-xs text-muted-foreground/80">
                        {t.chat.rule}: {step.rule_id}
                      </p>
                    ) : null}
                    {step.status !== "done" && step.detail === undefined ? (
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Icon className="size-3" />
                        {t.chat.status[step.status]}
                      </p>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
          {toolCalls.length > 0 ? (
            <div className="mt-3 space-y-2 border-t border-border pt-3">
              <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                <TerminalIcon className="size-3" />
                {t.chat.toolCalls}
              </p>
              {toolCalls.map((call, index) => (
                <ToolCallTrace
                  key={call.tool_call_id ?? `${call.name}:${index}`}
                  call={call}
                />
              ))}
            </div>
          ) : null}
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>
  );
}
