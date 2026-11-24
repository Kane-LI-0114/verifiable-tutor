import { CheckCircle2Icon, FlaskConicalIcon, XCircleIcon } from "lucide-react";

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
import type { TestSuite } from "@/lib/types";

export function TestResults({ suites }: { suites: TestSuite[] }) {
  const t = useT();
  const cases = suites.flatMap((suite) => suite.cases);
  const passed = cases.filter((testCase) => testCase.status === "passed").length;

  if (cases.length === 0) {
    return null;
  }

  return (
    <Trace>
      <TraceCollapsible defaultOpen>
        <TraceCollapsibleTrigger>
          <TraceLine>
            <TraceIcon>
              <FlaskConicalIcon />
            </TraceIcon>
            <TraceTitle>{t.practice.testResults}</TraceTitle>
            <TraceDescription>
              {format(
                cases.length === 1 ? t.practice.suitesOne : t.practice.suites,
                { passed, total: cases.length },
              )}
            </TraceDescription>
          </TraceLine>
        </TraceCollapsibleTrigger>
        <TraceCollapsibleContent>
          <div className="space-y-3">
            {suites.map((suite) => (
              <div key={suite.name} className="space-y-1">
                <p className="font-mono text-xs text-muted-foreground">{suite.name}</p>
                <ul className="space-y-1">
                  {suite.cases.map((testCase) => (
                    <li key={testCase.name} className="flex items-start gap-2 text-sm">
                      {testCase.status === "passed" ? (
                        <CheckCircle2Icon className="mt-0.5 size-3.5 shrink-0 text-primary" />
                      ) : (
                        <XCircleIcon className="mt-0.5 size-3.5 shrink-0 text-destructive" />
                      )}
                      <span className="min-w-0">
                        <span className="block">{testCase.name}</span>
                        {testCase.message ? (
                          <span className="block font-mono text-xs text-destructive">
                            {testCase.message}
                          </span>
                        ) : null}
                      </span>
                      {testCase.duration_ms === undefined ? null : (
                        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                          {testCase.duration_ms} ms
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>
  );
}
