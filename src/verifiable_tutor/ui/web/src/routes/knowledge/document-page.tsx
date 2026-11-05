import { ArrowLeftIcon, ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";

import { DocChatPane } from "@/components/knowledge/doc-chat-pane";
import { PdfCanvas } from "@/components/knowledge/pdf-canvas";
import { SidePane } from "@/components/layout/side-pane";
import { PageError, PageLoading } from "@/components/layout/page-states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetchBinary } from "@/lib/api/client";
import { knowledgeApi, type KnowledgeDocument } from "@/lib/api/knowledge";
import { format, useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";

const PANE_WIDTH_KEY = "vt.knowledge.chat.width";
const PANE_COLLAPSED_KEY = "vt.knowledge.chat.collapsed";

function previewDocument(docId: string): KnowledgeDocument {
  return {
    id: docId,
    title: docId,
    filename: `${docId}.pdf`,
    folder_id: null,
    page_count: 67,
    chunk_count: 67,
    byte_size: 10470744,
    status: "ready",
    status_detail: null,
    summary: "Preview summary written by Qwen on TACC.",
    summary_model: "qwen3.8-27b",
    created_at: "2026-11-05T04:00:00+00:00",
    indexed_at: "2026-11-05T04:20:00+00:00",
    pdf_url: `/api/knowledge/documents/${docId}/file`,
    thumbnail_url: `/api/corpus/${docId}/pages/1.webp`,
  };
}

export function DocumentPage() {
  const t = useT();
  const navigate = useNavigate();
  const { isPreview } = usePreview();
  const params = useParams<{ docId: string }>();
  const docId = params.docId ?? "";
  const [search, setSearch] = useSearchParams();
  const requestedPage = Number(search.get("page") ?? "1");
  const from = search.get("from");

  const [document, setDocument] = useState<KnowledgeDocument | null>(
    isPreview ? previewDocument(docId) : null,
  );
  const [pdf, setPdf] = useState<ArrayBuffer | null>(null);
  const [failed, setFailed] = useState(false);
  const [pageInput, setPageInput] = useState(String(requestedPage));
  const [paneCollapsed, setPaneCollapsed] = useState(false);

  const pageCount = document?.page_count ?? 1;
  const page = useMemo(
    () => Math.min(Math.max(Number.isFinite(requestedPage) ? requestedPage : 1, 1), pageCount),
    [pageCount, requestedPage],
  );

  useEffect(() => {
    setPageInput(String(page));
  }, [page]);

  useEffect(() => {
    if (isPreview) {
      setDocument(previewDocument(docId));
      return;
    }
    const controller = new AbortController();
    setFailed(false);
    knowledgeApi
      .document(docId, controller.signal)
      .then(setDocument)
      .catch((error: unknown) => {
        if ((error as { name?: string }).name !== "AbortError") {
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [docId, isPreview]);

  useEffect(() => {
    if (isPreview) {
      return;
    }
    const controller = new AbortController();
    apiFetchBinary(`/api/knowledge/documents/${docId}/file`, {
      signal: controller.signal,
    })
      .then(setPdf)
      .catch((error: unknown) => {
        if ((error as { name?: string }).name !== "AbortError") {
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [docId, isPreview]);

  function goToPage(next: number) {
    const clamped = Math.min(Math.max(next, 1), pageCount);
    const params = new URLSearchParams(search);
    params.set("page", String(clamped));
    setSearch(params, { replace: true });
  }

  function back() {
    if (from) {
      navigate(`/knowledge?folder=${encodeURIComponent(from)}`);
    } else {
      navigate("/knowledge");
    }
  }

  if (failed) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center">
        <PageError title={t.common.errorTitle} description={t.common.errorBody} />
      </div>
    );
  }
  if (document === null) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center">
        <PageLoading label={t.knowledge.loadingPdf} />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1">
      <section className="flex min-w-0 flex-1 flex-col" aria-label={t.knowledge.previewTitle}>
        <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={t.knowledge.backToKnowledge}
            title={t.knowledge.backToKnowledge}
            onClick={back}
          >
            <ArrowLeftIcon />
          </Button>
          <h1 className="min-w-0 truncate text-sm font-medium">{document.filename}</h1>
          <div className="ml-auto flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={t.knowledge.previousPage}
              title={t.knowledge.previousPage}
              disabled={page <= 1}
              onClick={() => goToPage(page - 1)}
            >
              <ChevronLeftIcon />
            </Button>
            <span className="text-sm tabular-nums" aria-live="polite">
              {format(t.knowledge.pageIndicator, { page, total: pageCount })}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={t.knowledge.nextPage}
              title={t.knowledge.nextPage}
              disabled={page >= pageCount}
              onClick={() => goToPage(page + 1)}
            >
              <ChevronRightIcon />
            </Button>
            <form
              className="ml-2 flex items-center gap-1"
              onSubmit={(event) => {
                event.preventDefault();
                goToPage(Number(pageInput));
              }}
            >
              <Input
                aria-label={t.knowledge.goToPage}
                className="h-8 w-16"
                inputMode="numeric"
                value={pageInput}
                onChange={(event) => setPageInput(event.target.value)}
              />
              <Button type="submit" variant="outline" size="sm">
                {t.knowledge.jump}
              </Button>
            </form>
          </div>
        </div>
        <div
          className="min-h-0 flex-1 overflow-auto bg-muted/40 p-4"
          onKeyDown={(event) => {
            if (event.key === "PageDown") {
              event.preventDefault();
              goToPage(page + 1);
            } else if (event.key === "PageUp") {
              event.preventDefault();
              goToPage(page - 1);
            }
          }}
          tabIndex={-1}
        >
          <PdfCanvas
            data={pdf}
            page={page}
            label={format(t.knowledge.pageIndicator, { page, total: pageCount })}
          />
        </div>
      </section>

      <SidePane
        testId="document-chat-pane"
        label={t.knowledge.chatTitle}
        collapsedLabel={t.knowledge.chatTitle}
        collapseLabel={t.chat.evidenceCollapse}
        expandLabel={t.chat.evidenceExpand}
        resizeLabel={t.chat.evidenceResize}
        widthKey={PANE_WIDTH_KEY}
        collapsedKey={PANE_COLLAPSED_KEY}
        collapsed={paneCollapsed}
        onCollapsedChange={setPaneCollapsed}
        header={t.knowledge.chatTitle}
        defaultWidth={400}
      >
        <DocChatPane docId={docId} pageNo={page} />
      </SidePane>
    </div>
  );
}
