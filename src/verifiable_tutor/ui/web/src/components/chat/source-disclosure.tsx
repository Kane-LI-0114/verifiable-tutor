import { ChevronDownIcon } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { SourceList } from "@/components/chat/source-list";
import { SourceThumbnail } from "@/components/chat/source-thumbnail";
import {
  AvatarGroup,
  AvatarGroupCount,
} from "@/components/ui/avatar";
import { sourceSummaryLabel } from "@/lib/chat/source-summary";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { CitationSource } from "@/lib/types";

const PREVIEW_THUMBNAILS = 3;

/**
 * A full-width citation strip that closes the answer, as opposed to the
 * capsule that opens the source pane. It starts folded to the same thumbnail
 * stack the capsule shows, so an answer reads as prose first; unfolding
 * reveals the same rows as the main source pane, in place.
 */
export function SourceDisclosure({ sources }: { sources: CitationSource[] }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const previews = useMemo(
    () => sources.slice(0, PREVIEW_THUMBNAILS),
    [sources],
  );
  const extra = sources.length - previews.length;
  const label = useMemo(() => sourceSummaryLabel(sources, t), [sources, t]);

  return (
    <div className="w-full overflow-hidden rounded-xl border bg-muted/20">
      <button
        type="button"
        className={cn(
          "flex h-9 w-full items-center gap-2 px-2 text-left outline-none",
          "transition-colors hover:bg-muted/60",
          "focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-inset",
          open && "bg-muted/40",
        )}
        aria-label={`${t.chat.sourcesTitle}: ${label}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        <AvatarGroup>
          {previews.map((source) => (
            <SourceThumbnail
              key={`${source.kind}:${source.marker}`}
              source={source}
            />
          ))}
          {extra > 0 ? (
            <AvatarGroupCount className="size-6 text-[0.65rem]">
              +{extra}
            </AvatarGroupCount>
          ) : null}
        </AvatarGroup>
        <span className="min-w-0 flex-1 truncate text-xs tabular-nums text-muted-foreground">
          {label}
        </span>
        <ChevronDownIcon
          aria-hidden="true"
          className={cn(
            "size-3.5 shrink-0 text-muted-foreground transition-transform duration-200 motion-reduce:transition-none",
            open && "rotate-180",
          )}
        />
      </button>
      {open ? (
        <div
          id={panelId}
          className="animate-in border-t bg-background p-1.5 fade-in-0 duration-150 motion-reduce:animate-none slide-in-from-top-1"
        >
          <SourceList sources={sources} />
        </div>
      ) : null}
    </div>
  );
}
