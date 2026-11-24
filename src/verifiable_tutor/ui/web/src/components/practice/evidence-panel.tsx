import { ChevronLeftIcon, ChevronRightIcon, FileImageIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { format, useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

function HighlightBox({
  box,
}: {
  box: [number, number, number, number];
}) {
  const [x1, y1, x2, y2] = box;
  return (
    <span
      className="pointer-events-none absolute rounded-sm border-2 border-primary bg-primary/15"
      style={{
        left: `${x1 * 100}%`,
        top: `${y1 * 100}%`,
        width: `${Math.max(x2 - x1, 0) * 100}%`,
        height: `${Math.max(y2 - y1, 0) * 100}%`,
      }}
    />
  );
}

export function EvidencePanel({
  citations,
  activeIndex,
  onSelect,
  className,
}: {
  citations: Citation[];
  activeIndex: number | null;
  onSelect: (index: number) => void;
  className?: string;
}) {
  const t = useT();
  const { isPreview, pageState } = usePreview();
  const [imageFailed, setImageFailed] = useState(false);

  const active = activeIndex === null ? null : citations[activeIndex] ?? null;
  const activeKey = active ? `${active.doc_id}:${active.page_no}` : "";

  // A new citation is a new image; an earlier load failure must not stick.
  useEffect(() => {
    setImageFailed(false);
  }, [activeKey]);

  if (pageState === "loading") {
    return (
      <div className={cn("space-y-3 p-4", className)} aria-busy="true">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="aspect-3/4 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (pageState === "error") {
    return (
      <div className={cn("p-4", className)}>
        <Alert variant="destructive">
          <AlertDescription>{t.chat.evidenceNotFound}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!active) {
    return (
      <div className={cn("flex h-full items-center justify-center p-6", className)}>
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileImageIcon />
            </EmptyMedia>
            <EmptyTitle>{t.chat.evidenceEmpty}</EmptyTitle>
            <EmptyDescription>{t.chat.evidenceEmptyBody}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </div>
    );
  }

  const imageUrl = `/api/corpus/${active.doc_id}/pages/${active.page_no}.webp`;

  return (
    <div className={cn("flex h-full min-h-0 flex-col", className)}>
      <div className="flex items-center gap-2 border-b p-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">
            {format(t.chat.evidencePage, {
              page: active.page_no,
              doc: active.doc_id,
            })}
          </p>
          <Badge variant="outline" className="mt-1">
            {t.chat.evidenceQuote}
          </Badge>
        </div>
        <div className="ml-auto flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={t.chat.evidencePrevious}
            disabled={activeIndex === null || activeIndex <= 0}
            onClick={() => activeIndex !== null && onSelect(activeIndex - 1)}
          >
            <ChevronLeftIcon />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={t.chat.evidenceNext}
            disabled={activeIndex === null || activeIndex >= citations.length - 1}
            onClick={() => activeIndex !== null && onSelect(activeIndex + 1)}
          >
            <ChevronRightIcon />
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <div className="relative aspect-3/4 w-full overflow-hidden rounded-md border bg-muted/40">
          {isPreview ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center text-xs text-muted-foreground">
              <FileImageIcon className="size-6" />
              <span className="font-medium text-foreground">
                {t.chat.evidencePreviewNotice}
              </span>
            </div>
          ) : imageFailed ? (
            <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-xs text-muted-foreground">
              {t.chat.evidenceNotFound}
            </div>
          ) : (
            <img
              src={imageUrl}
              alt={format(t.chat.evidencePage, {
                page: active.page_no,
                doc: active.doc_id,
              })}
              className="absolute inset-0 size-full object-contain"
              onError={() => setImageFailed(true)}
            />
          )}
          {active.bbox_norm ? <HighlightBox box={active.bbox_norm} /> : null}
        </div>

        <blockquote className="prose-quote mt-3 border-l-2 pl-3 text-sm">
          {active.quote}
        </blockquote>
        <p className="mt-2 text-xs text-muted-foreground">
          {active.doc_id} · {format(t.chat.sourcePage, { page: active.page_no })}
        </p>
      </div>
    </div>
  );
}
