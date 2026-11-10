import { CheckIcon, CopyIcon, RotateCcwIcon, Volume2Icon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { Button } from "@/components/ui/button";
import { Message, MessageContent, MessageFooter } from "@/components/ui/message";
import { Markdown } from "@/components/ai/markdown";
import { AnswerPending } from "@/components/chat/answer-pending";
import { CitationRow } from "@/components/chat/citation-row";
import { PageError } from "@/components/layout/page-states";
import { SourcesList } from "@/components/chat/sources";
import { WorkChain } from "@/components/chat/work-chain";
import { useT } from "@/lib/i18n";
import { synthesizeSpeech } from "@/lib/api/voice";
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
  const [speechState, setSpeechState] = useState<"idle" | "loading">("idle");
  const copyTimer = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // The feedback timer must not outlive the answer it belongs to.
  useEffect(() => {
    return () => {
      if (copyTimer.current !== null) {
        window.clearTimeout(copyTimer.current);
      }
    };
  }, []);

  async function copy() {
    try {
      await navigator.clipboard?.writeText(content);
      setCopied(true);
      if (copyTimer.current !== null) {
        window.clearTimeout(copyTimer.current);
      }
      copyTimer.current = window.setTimeout(() => {
        setCopied(false);
        copyTimer.current = null;
      }, 1500);
    } catch {
      setCopied(false);
    }
  }

  async function speak() {
    if (speechState === "loading") {
      return;
    }
    setSpeechState("loading");
    const blob = await synthesizeSpeech(content);
    const audio = audioRef.current;
    if (audio === null) {
      return;
    }
    audio.src = URL.createObjectURL(blob);
    await audio.play();
    setSpeechState("idle");
  }

  return (
    <MessageFooter
      role="group"
      className="gap-1"
      aria-label={t.chat.answerActions}
    >
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
        aria-busy={speechState === "loading"}
        disabled={speechState === "loading"}
        onClick={speak}
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
      <audio ref={audioRef} className="hidden" />
    </MessageFooter>
  );
}

export function ChatMessageView({
  turn,
  onOpenCitation,
  failed = false,
  streaming = false,
  onRetry,
}: {
  turn: ConversationTurn;
  onOpenCitation: (citation: Citation) => void;
  failed?: boolean;
  streaming?: boolean;
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
        {meta &&
        (meta.work_steps.length > 0 || (meta.events ?? []).length > 0) ? (
          <WorkChain
            steps={meta.work_steps}
            policy={meta.policy_state}
            events={meta.events ?? []}
          />
        ) : null}
        {failed ? (
          <PageError
            title={t.chat.errorTitle}
            description={t.chat.errorBody}
            onRetry={onRetry}
          />
        ) : message.content === "" && streaming ? (
          <AnswerPending />
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
