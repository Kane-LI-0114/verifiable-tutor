import { Button } from "@/components/ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { format, useT } from "@/lib/i18n";
import type { Citation } from "@/lib/types";

export function CitationRow({
  citations,
  onOpen,
}: {
  citations: Citation[];
  onOpen: (citation: Citation) => void;
}) {
  const t = useT();

  if (citations.length === 0) {
    return null;
  }

  return (
    <div
      className="flex flex-wrap items-center gap-1.5"
      aria-label={t.chat.citations}
    >
      <span className="text-xs text-muted-foreground">{t.chat.citations}</span>
      {citations.map((citation, index) => (
        <HoverCard key={`${citation.doc_id}:${citation.page_no}:${index}`}>
          <HoverCardTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-6 rounded-full px-2 font-mono text-xs"
              onClick={() => onOpen(citation)}
              aria-label={format(t.chat.openEvidence, { page: citation.page_no })}
            >
              [{index + 1}]
            </Button>
          </HoverCardTrigger>
          <HoverCardContent className="w-80 space-y-2" align="start">
            <p className="text-xs text-muted-foreground">
              {citation.doc_id} · {format(t.chat.sourcePage, { page: citation.page_no })}
            </p>
            <blockquote className="border-l-2 pl-2 text-sm">
              {citation.quote}
            </blockquote>
            <Button
              type="button"
              variant="link"
              size="sm"
              className="h-auto px-0"
              onClick={() => onOpen(citation)}
            >
              {format(t.chat.openEvidence, { page: citation.page_no })}
            </Button>
          </HoverCardContent>
        </HoverCard>
      ))}
    </div>
  );
}
