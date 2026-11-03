import { BookOpenIcon, ExternalLinkIcon } from "lucide-react";

import {
  Trace,
  TraceCollapsible,
  TraceCollapsibleContent,
  TraceCollapsibleTrigger,
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import { format, useT } from "@/lib/i18n";
import type { Citation } from "@/lib/types";

export function SourcesList({
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
    <Trace>
      <TraceCollapsible>
        <TraceCollapsibleTrigger>
          <TraceLine>
            <TraceIcon>
              <BookOpenIcon />
            </TraceIcon>
            <TraceTitle>
              {t.chat.sources} · {citations.length}
            </TraceTitle>
          </TraceLine>
        </TraceCollapsibleTrigger>
        <TraceCollapsibleContent>
          <ol className="space-y-2">
            {citations.map((citation, index) => (
              <li key={`${citation.doc_id}:${citation.page_no}:${index}`}>
                <button
                  type="button"
                  className="group flex w-full items-start gap-2 rounded-md p-1 text-left hover:bg-muted"
                  onClick={() => onOpen(citation)}
                >
                  <span className="mt-0.5 font-mono text-xs text-muted-foreground">
                    [{index + 1}]
                  </span>
                  <span className="min-w-0 space-y-0.5">
                    <span className="block text-xs text-muted-foreground">
                      {citation.doc_id} ·{" "}
                      {format(t.chat.sourcePage, { page: citation.page_no })}
                    </span>
                    <span className="block text-sm text-foreground">
                      {citation.quote}
                    </span>
                  </span>
                  <ExternalLinkIcon className="ml-auto mt-1 size-3.5 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100" />
                </button>
              </li>
            ))}
          </ol>
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>
  );
}
