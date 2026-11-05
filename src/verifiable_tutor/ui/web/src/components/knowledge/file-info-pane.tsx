import { BookOpenIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { apiFetch } from "@/lib/api/client";
import type { KnowledgeDocument } from "@/lib/api/knowledge";
import type { KnowledgeCard } from "@/lib/types";
import { format, useT } from "@/lib/i18n";
import { StatusBadge } from "@/components/knowledge/tiles";

function statusLabel(status: KnowledgeDocument["status"], t: ReturnType<typeof useT>): string {
  return {
    uploading: t.knowledge.statusUploading,
    uploaded: t.knowledge.statusUploaded,
    upload_failed: t.knowledge.statusFailed,
    processing: t.knowledge.statusProcessing,
    ready: t.knowledge.statusReady,
    failed: t.knowledge.statusFailed,
  }[status];
}

function formatDate(iso: string | null): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString();
}

function CardsSection({ docId }: { docId: string }) {
  const t = useT();
  const [cards, setCards] = useState<KnowledgeCard[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setCards(null);
    apiFetch<{ cards: KnowledgeCard[] }>(
      `/api/knowledge/cards?doc_id=${encodeURIComponent(docId)}`,
      { signal: controller.signal },
    )
      .then((body) => setCards(body.cards))
      .catch(() => setCards([]));
    return () => controller.abort();
  }, [docId]);

  if (cards === null || cards.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2">
      <h3 className="text-xs font-medium tracking-wide text-muted-foreground">
        {t.knowledge.cards}
      </h3>
      <ul className="space-y-1">
        {cards.slice(0, 5).map((card) => (
          <li key={card.chunk_id} className="rounded-md border p-2 text-xs">
            <div className="flex items-center gap-1">
              <Badge variant="outline">{format(t.knowledge.page, { page: card.page_no })}</Badge>
              <span className="ml-auto text-muted-foreground">
                {format(t.knowledge.citationCount, { count: card.citations.length })}
              </span>
            </div>
            <p className="mt-1 text-muted-foreground">{card.summary}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The right-hand record of the selected file. */
export function FileInfoPane({
  document,
  preview,
  onAsk,
}: {
  document: KnowledgeDocument | null;
  preview: boolean;
  onAsk: (docId: string) => void;
}) {
  const t = useT();

  if (document === null) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-6 text-center">
        <p className="text-sm text-muted-foreground">{t.knowledge.selectedEmpty}</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <section data-testid="file-info-header" className="shrink-0 space-y-1 p-4">
        <h2 className="text-sm font-semibold break-words">{document.title}</h2>
        <div className="flex items-center gap-2">
          <StatusBadge status={document.status} />
          <span className="truncate text-xs text-muted-foreground">
            {document.filename}
          </span>
        </div>
      </section>

      <Separator />

      <div
        data-testid="file-info-scroll"
        className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4"
      >
        <section className="space-y-1">
          <h3 className="text-xs font-medium tracking-wide text-muted-foreground">
            {t.knowledge.summary}
          </h3>
          {document.summary ? (
            <>
              <p className="max-w-[60ch] text-sm leading-relaxed">
                {document.summary}
              </p>
              {document.summary_model ? (
                <p className="text-xs text-muted-foreground">
                  {format(t.knowledge.summaryModel, { model: document.summary_model })}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">{t.knowledge.summaryMissing}</p>
          )}
        </section>

        {preview ? null : <CardsSection docId={document.id} />}
      </div>

      <div
        data-testid="file-info-footer"
        className="shrink-0 space-y-3 border-t p-4"
      >
        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
          <div>
            <dt className="text-muted-foreground">{t.knowledge.added}</dt>
            <dd>{formatDate(document.created_at)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t.knowledge.pages}</dt>
            <dd>{document.page_count}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t.knowledge.chunks}</dt>
            <dd>{document.chunk_count}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t.knowledge.statusLabel}</dt>
            <dd>{statusLabel(document.status, t)}</dd>
          </div>
        </dl>

        {document.status_detail ? (
          <p className="text-xs text-muted-foreground">{document.status_detail}</p>
        ) : null}

        <Button type="button" className="w-full" onClick={() => onAsk(document.id)}>
          <BookOpenIcon />
          {t.knowledge.askAboutFile}
        </Button>
      </div>
    </div>
  );
}
