import {
  ArrowLeftIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MessageSquareIcon,
  RectangleVerticalIcon,
  Rows3Icon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";

import { DocChatPane } from "@/components/knowledge/doc-chat-pane";
import { PdfViewer } from "@/components/knowledge/pdf-viewer";
import { readCollapsed, SidePane, writeCollapsed } from "@/components/layout/side-pane";
import { PageError, PageLoading } from "@/components/layout/page-states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useMediaQuery } from "@/lib/use-media-query";
import { apiFetchBinary } from "@/lib/api/client";
import { knowledgeApi, type KnowledgeDocument } from "@/lib/api/knowledge";
import { format, useT } from "@/lib/i18n";
import {
  clearDocumentPath,
  rememberDocumentPath,
} from "@/lib/knowledge/return-path";
import { usePreview } from "@/lib/preview/context";
import { cn } from "@/lib/utils";

const PANE_WIDTH_KEY = "vt.knowledge.chat.width";
const PANE_COLLAPSED_KEY = "vt.knowledge.chat.collapsed";
const BROWSE_MODE_KEY = "vt.knowledge.preview.mode";

type BrowseMode = "page" | "scroll";

function readBrowseMode(): BrowseMode {
  try {
    return window.localStorage.getItem(BROWSE_MODE_KEY) === "scroll" ? "scroll" : "page";
  } catch {
    return "page";
  }
}

function writeBrowseMode(mode: BrowseMode) {
  try {
    window.localStorage.setItem(BROWSE_MODE_KEY, mode);
  } catch {
    // A private window with storage disabled keeps the in-memory choice.
  }
}

function modeButtonClass(active: boolean): string {
  return cn(
    "inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-xs font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50 motion-reduce:transition-none",
    active
      ? "bg-background text-foreground shadow-sm"
      : "text-muted-foreground hover:text-foreground",
  );
}

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
  const [pageInput, setPageInput] = useState("");
  const [browseMode, setBrowseMode] = useState<BrowseMode>(readBrowseMode);
  const [scrollToken, setScrollToken] = useState(0);
  // The scroll target is set from the click, not read back from the URL: the
  // router applies the page change a render later than the token.
  const [scrollTarget, setScrollTarget] = useState(
    Number.isFinite(requestedPage) ? requestedPage : 1,
  );
  const [paneCollapsed, setPaneCollapsed] = useState(() =>
    readCollapsed(PANE_COLLAPSED_KEY),
  );
  const [chatOpen, setChatOpen] = useState(false);
  const isNarrow = useMediaQuery("(max-width: 1023px)");

  const pageCount = document?.page_count ?? 1;
  const page = useMemo(
    () => Math.min(Math.max(Number.isFinite(requestedPage) ? requestedPage : 1, 1), pageCount),
    [pageCount, requestedPage],
  );

  // Keep the knowledge nav pointed at this file while the reader is here, so
  // leaving for the conversation view and coming back lands on the same page.
  // The memory is in the tab, not storage: a reload starts at the grid.
  const returnPath = useMemo(() => {
    const params = new URLSearchParams({ page: String(page) });
    if (from) {
      params.set("from", from);
    }
    return `/knowledge/docs/${encodeURIComponent(docId)}?${params.toString()}`;
  }, [docId, from, page]);
  useEffect(() => {
    rememberDocumentPath(returnPath);
  }, [returnPath]);

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
    // A page box that holds letters parses to NaN; keep the current page
    // instead of writing NaN into the URL.
    const target = Number.isFinite(next) ? next : page;
    const clamped = Math.min(Math.max(target, 1), pageCount);
    const params = new URLSearchParams(search);
    params.set("page", String(clamped));
    setSearch(params, { replace: true });
    setScrollTarget(clamped);
    if (browseMode === "scroll") {
      setScrollToken((token) => token + 1);
    }
  }

  function chooseMode(next: BrowseMode) {
    if (next === browseMode) {
      return;
    }
    setBrowseMode(next);
    writeBrowseMode(next);
    if (next === "scroll") {
      setScrollTarget(page);
      setScrollToken((token) => token + 1);
    }
  }

  function jumpToPage() {
    const typed = pageInput.trim();
    if (typed === "") {
      return;
    }
    const target = Number(typed);
    if (!Number.isFinite(target)) {
      return;
    }
    goToPage(target);
    setPageInput("");
  }

  // Scroll mode reports the page being read so the URL, the indicator, and the
  // chat context stay on it without pushing history entries.
  function recordVisiblePage(next: number) {
    const clamped = Math.min(Math.max(next, 1), pageCount);
    if (clamped === page) {
      return;
    }
    const params = new URLSearchParams(search);
    params.set("page", String(clamped));
    setSearch(params, { replace: true });
  }

  function back() {
    clearDocumentPath();
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
          {isNarrow ? (
            <Button
              type="button"
              variant="outline"
              size="icon-sm"
              aria-label={t.knowledge.chatTitle}
              title={t.knowledge.chatTitle}
              onClick={() => setChatOpen(true)}
            >
              <MessageSquareIcon />
            </Button>
          ) : null}
          <div className="ml-auto flex items-center gap-1">
            <div
              role="group"
              aria-label={t.knowledge.browseMode}
              className="mr-1 flex items-center rounded-lg border bg-muted/40 p-0.5"
            >
              <button
                type="button"
                aria-pressed={browseMode === "page"}
                aria-label={t.knowledge.pageView}
                title={t.knowledge.pageViewHint}
                onClick={() => chooseMode("page")}
                className={modeButtonClass(browseMode === "page")}
              >
                <RectangleVerticalIcon className="size-3.5" />
                <span className="hidden sm:inline">{t.knowledge.pageView}</span>
              </button>
              <button
                type="button"
                aria-pressed={browseMode === "scroll"}
                aria-label={t.knowledge.scrollView}
                title={t.knowledge.scrollViewHint}
                onClick={() => chooseMode("scroll")}
                className={modeButtonClass(browseMode === "scroll")}
              >
                <Rows3Icon className="size-3.5" />
                <span className="hidden sm:inline">{t.knowledge.scrollView}</span>
              </button>
            </div>
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
            <span
              className="text-sm tabular-nums"
              aria-live={browseMode === "page" ? "polite" : "off"}
            >
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
                jumpToPage();
              }}
            >
              <Input
                aria-label={t.knowledge.goToPage}
                className="h-8 w-16"
                inputMode="numeric"
                placeholder={t.knowledge.pagePlaceholder}
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
          className="min-h-0 flex-1 bg-muted/40"
          onKeyDown={
            browseMode === "page"
              ? (event) => {
                  if (event.key === "PageDown") {
                    event.preventDefault();
                    goToPage(page + 1);
                  } else if (event.key === "PageUp") {
                    event.preventDefault();
                    goToPage(page - 1);
                  }
                }
              : undefined
          }
          tabIndex={-1}
        >
          <PdfViewer
            data={pdf}
            mode={browseMode}
            page={page}
            scrollToken={scrollToken}
            scrollTarget={scrollTarget}
            onVisiblePage={recordVisiblePage}
            labelFor={(nextPage) =>
              format(t.knowledge.pageIndicator, { page: nextPage, total: pageCount })
            }
          />
        </div>
      </section>

      {isNarrow ? (
        <Sheet open={chatOpen} onOpenChange={setChatOpen}>
          <SheetContent side="right" className="flex w-full flex-col p-0 sm:max-w-md">
            <SheetHeader className="border-b">
              <SheetTitle>{t.knowledge.chatTitle}</SheetTitle>
            </SheetHeader>
            <DocChatPane key={docId} docId={docId} pageNo={page} />
          </SheetContent>
        </Sheet>
      ) : (
      <SidePane
        testId="document-chat-pane"
        label={t.knowledge.chatTitle}
        collapsedLabel={t.knowledge.chatTitle}
        collapseLabel={t.knowledge.paneCollapse}
        expandLabel={t.knowledge.paneExpand}
        resizeLabel={t.knowledge.paneResize}
        widthKey={PANE_WIDTH_KEY}
        collapsed={paneCollapsed}
        onCollapsedChange={(next) => {
          setPaneCollapsed(next);
          writeCollapsed(PANE_COLLAPSED_KEY, next);
        }}
        header={t.knowledge.chatTitle}
        defaultWidth={400}
      >
        <DocChatPane key={docId} docId={docId} pageNo={page} />
      </SidePane>
      )}
    </div>
  );
}
