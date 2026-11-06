import { TerminalIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { CodeBlock, CodeBlockContent } from "@/components/ui/code-block";
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
import { useT } from "@/lib/i18n";
import type { ToolCall } from "@/lib/types";

export function ToolCallTrace({ call }: { call: ToolCall }) {
  const t = useT();

  return (
    <Trace>
      <TraceCollapsible>
        <TraceCollapsibleTrigger>
          <TraceLine status={call.status === "failed" ? "error" : undefined}>
            <TraceIcon>
              <TerminalIcon />
            </TraceIcon>
            <TraceTitle>{`${t.chat.toolCall}: ${call.name}`}</TraceTitle>
            {call.exit_code === null ? null : (
              <TraceDescription>
                {t.chat.exitCode} {call.exit_code}
              </TraceDescription>
            )}
            {call.duration_ms === undefined ? null : (
              <TraceDescription>
                {t.chat.duration} {call.duration_ms} ms
              </TraceDescription>
            )}
            <Badge variant={call.status === "failed" ? "destructive" : "outline"}>
              {t.chat.status[call.status === "running" ? "started" : call.status]}
            </Badge>
          </TraceLine>
        </TraceCollapsibleTrigger>
        <TraceCollapsibleContent>
          {call.command.length > 0 ? (
            <>
              <p className="mb-1 text-xs text-muted-foreground">{t.chat.command}</p>
              <CodeBlock size="sm">
                <CodeBlockContent wrap className="max-h-48">
                  {call.command.join(" ")}
                </CodeBlockContent>
              </CodeBlock>
            </>
          ) : call.arguments === undefined ? null : (
            <>
              <p className="mb-1 text-xs text-muted-foreground">
                {t.chat.arguments}
              </p>
              <CodeBlock size="sm">
                <CodeBlockContent wrap className="max-h-48">
                  {JSON.stringify(call.arguments, null, 2)}
                </CodeBlockContent>
              </CodeBlock>
            </>
          )}
          {call.output ? (
            <>
              <p className="mb-1 mt-3 text-xs text-muted-foreground">
                {t.chat.output}
              </p>
              <CodeBlock size="sm">
                <CodeBlockContent wrap className="max-h-64">
                  {call.output}
                </CodeBlockContent>
              </CodeBlock>
            </>
          ) : null}
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>
  );
}
