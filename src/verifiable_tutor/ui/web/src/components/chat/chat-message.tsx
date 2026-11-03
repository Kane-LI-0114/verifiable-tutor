import { CheckIcon, CopyIcon, RotateCcwIcon, Volume2Icon } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { Button } from "@/components/ui/button";
import { Message, MessageContent, MessageFooter } from "@/components/ui/message";
import { Markdown } from "@/components/ai/markdown";
import { CitationRow } from "@/components/chat/citation-row";
import { PageError } from "@/components/layout/page-states";
import { ReasoningTrace } from "@/components/chat/reasoning-trace";
import { SourcesList } from "@/components/chat/sources";
import { ToolCallTrace } from "@/components/chat/tool-call";
import { WorkChain } from "@/components/chat/work-chain";
import { useT } from "@/lib/i18n";
import type { Citation, ConversationTurn } from "@/lib/types";

function AnswerActions({
  content,
  onRetry,
}: {
  content: string;
  onRetry?: () => void;
}) {
  const t = useT();
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard?.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <MessageFooter className="gap-1" aria-label={t.chat.answerActions}>
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        aria-label={t.chat.copyAnswer}
        onClick={copy}
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        aria-label={t.common.speak}
        disabled
        title={t.common.unavailable}
      >
        <Volume2Icon />
      </Button>
      {onRetry ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          aria-label={t.chat.retry}
          onClick={onRetry}
        >
          <RotateCcwIcon />
        </Button>
      ) : null}
    </MessageFooter>
  );
}

export function ChatMessageView({
  turn,
  onOpenCitation,
  failed = false,
  onRetry,
}: {
  turn: ConversationTurn;
  onOpenCitation: (citation: Citation) => void;
  failed?: boolean;
  onRetry?: () => void;
}) {
  const t = useT();
  const { message, meta } = turn;

  if (message.role === "user") {
    return (
      <Message align="end">
        <MessageContent>
          <Bubble align="end">
            <BubbleContent>{message.content}</BubbleContent>
          </Bubble>
        </MessageContent>
      </Message>
    );
  }

  return (
    <Message>
      <MessageContent>
        {meta ? <WorkChain steps={meta.work_steps} policy={meta.policy_state} /> : null}
        {meta?.reasoning ? <ReasoningTrace reasoning={meta.reasoning} /> : null}
        {failed ? (
          <PageError
            title={t.chat.errorTitle}
            description={t.chat.errorBody}
            onRetry={onRetry}
          />
        ) : (
          <>
            <Markdown>{message.content}</Markdown>
            {meta ? (
              <CitationRow
                citations={meta.citations}
                onOpen={onOpenCitation}
              />
            ) : null}
            {meta ? (
              <SourcesList
                citations={meta.citations}
                onOpen={onOpenCitation}
              />
            ) : null}
            {meta?.tool_calls.map((call) => (
              <ToolCallTrace key={`${call.name}:${call.command.join(" ")}`} call={call} />
            ))}
          </>
        )}
        <div className="flex items-center gap-2">
          <AnswerActions content={message.content} onRetry={onRetry} />
          <Badge variant="outline">
            {message.provider ?? "provider"} · {message.tier ?? "tier"}
          </Badge>
        </div>
      </MessageContent>
    </Message>
  );
}
