import { memo, useCallback, useEffect, useRef, useState } from "react";

import { useT } from "@/lib/i18n";

type PdfPage = {
  getViewport: (options: { scale: number }) => { width: number; height: number };
  render: (options: Record<string, unknown>) => { promise: Promise<void> };
};

type PdfDocument = {
  numPages: number;
  getPage: (page: number) => Promise<PdfPage>;
  destroy?: () => Promise<void>;
};

type PdfModule = {
  GlobalWorkerOptions: { workerSrc: string };
  getDocument: (options: { data: ArrayBuffer }) => {
    promise: Promise<PdfDocument>;
  };
};

let pdfModule: Promise<PdfModule> | null = null;

/**
 * Load pdf.js and its worker on first use.
 *
 * The viewer is the heaviest thing on the knowledge page, so the library is a
 * dynamic import: a reader who never opens a document never downloads it.
 */
async function loadPdf(): Promise<PdfModule> {
  if (pdfModule === null) {
    pdfModule = (async () => {
      const [pdfjs, worker] = await Promise.all([
        import("pdfjs-dist") as Promise<unknown>,
        import("pdfjs-dist/build/pdf.worker.min.mjs?url") as Promise<{
          default: string;
        }>,
      ]);
      const module = pdfjs as PdfModule;
      module.GlobalWorkerOptions.workerSrc = worker.default;
      return module;
    })();
  }
  return pdfModule;
}

/**
 * Load the document once per file.
 *
 * Page changes then reuse the parsed document, so turning a page does not
 * re-download or re-parse the whole PDF.
 */
function usePdfDocument(data: ArrayBuffer | null) {
  const [pdfDocument, setPdfDocument] = useState<PdfDocument | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let loaded: PdfDocument | null = null;
    setPdfDocument(null);
    setFailed(false);
    if (data === null) {
      return;
    }

    loadPdf()
      .then((pdfjs) => pdfjs.getDocument({ data: data.slice(0) }).promise)
      .then((next) => {
        loaded = next;
        if (cancelled) {
          void next.destroy?.();
          return;
        }
        setPdfDocument(next);
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
        }
      });

    return () => {
      cancelled = true;
      if (loaded !== null) {
        void loaded.destroy?.();
      }
    };
  }, [data]);

  return { pdfDocument, failed };
}

const PdfPageCanvas = memo(function PdfPageCanvas({
  pdfDocument,
  page,
  label,
  fit,
}: {
  pdfDocument: PdfDocument;
  page: number;
  label: string;
  fit: "page" | "scroll";
}) {
  const t = useT();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);

    async function render() {
      try {
        const pdfPage = await pdfDocument.getPage(page);
        const viewport = pdfPage.getViewport({ scale: 1.5 });
        const canvas = canvasRef.current;
        if (canvas === null || cancelled) {
          return;
        }
        const context = canvas.getContext("2d");
        if (context === null) {
          return;
        }
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        await pdfPage.render({ canvasContext: context, viewport, canvas }).promise;
      } catch {
        if (!cancelled) {
          setFailed(true);
        }
      }
    }

    void render();
    return () => {
      cancelled = true;
    };
  }, [page, pdfDocument]);

  if (failed) {
    return (
      <p className="p-4 text-sm text-muted-foreground" role="alert">
        {t.knowledge.pdfError}
      </p>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      aria-label={label}
      className={
        fit === "page"
          ? "mx-auto block max-h-full max-w-full rounded-sm bg-white shadow-sm"
          : "block h-full w-full"
      }
    />
  );
});

/**
 * A continuous reader: every page keeps its place in the column, and only the
 * pages near the viewport get a canvas. That keeps scrolling smooth on a long
 * PDF without paying for hundreds of rendered pages up front.
 */
function PdfScrollView({
  pdfDocument,
  page,
  scrollToken,
  scrollTarget,
  onVisiblePage,
  labelFor,
}: {
  pdfDocument: PdfDocument;
  page: number;
  scrollToken: number;
  scrollTarget: number;
  onVisiblePage: (page: number) => void;
  labelFor: (page: number) => string;
}) {
  const t = useT();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const pageRefs = useRef<Array<HTMLDivElement | null>>([]);
  const pageRef = useRef(page);
  const onVisiblePageRef = useRef(onVisiblePage);
  const lastReported = useRef(0);
  const [sizes, setSizes] = useState<Array<{ width: number; height: number } | null>>(
    [],
  );
  const [rendered, setRendered] = useState<ReadonlySet<number>>(() => new Set());
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  pageRef.current = page;
  onVisiblePageRef.current = onVisiblePage;

  // Measure every page once so the column has its final shape before a page is
  // painted. Without this, jumping to page 50 would land at a guessed offset.
  useEffect(() => {
    let cancelled = false;
    setReady(false);
    setFailed(false);
    setRendered(new Set());
    pageRefs.current = [];
    setSizes(Array.from({ length: pdfDocument.numPages }, () => null));

    Promise.all(
      Array.from({ length: pdfDocument.numPages }, (_, index) =>
        pdfDocument
          .getPage(index + 1)
          .then((pdfPage) => {
            const viewport = pdfPage.getViewport({ scale: 1.5 });
            return { width: viewport.width, height: viewport.height };
          })
          .catch(() => null),
      ),
    ).then((next) => {
      if (cancelled) {
        return;
      }
      if (next.every((size) => size === null)) {
        setFailed(true);
        return;
      }
      setSizes(next);
      setReady(true);
    });

    return () => {
      cancelled = true;
    };
  }, [pdfDocument]);

  const measure = useCallback(() => {
    const container = scrollRef.current;
    if (container === null) {
      return;
    }

    // The page with the most overlap against the viewport is the page being
    // read. A zero-height container (jsdom, a hidden pane) keeps the URL page.
    let current = lastReported.current > 0 ? lastReported.current : pageRef.current;
    const height = container.clientHeight;
    if (height > 0) {
      const containerRect = container.getBoundingClientRect();
      let largestOverlap = 0;
      pageRefs.current.forEach((element, index) => {
        if (element === null) {
          return;
        }
        const rect = element.getBoundingClientRect();
        const overlap =
          Math.min(rect.bottom, containerRect.bottom) -
          Math.max(rect.top, containerRect.top);
        if (overlap > largestOverlap) {
          largestOverlap = overlap;
          current = index + 1;
        }
      });

      if (largestOverlap > 0 && current !== lastReported.current) {
        lastReported.current = current;
        onVisiblePageRef.current(current);
      }
    }

    const start = Math.max(1, current - 2);
    const end = Math.min(pdfDocument.numPages, current + 2);
    setRendered((previous) => {
      const next = new Set<number>();
      for (let number = start; number <= end; number += 1) {
        next.add(number);
      }
      if (
        next.size === previous.size &&
        Array.from(next).every((number) => previous.has(number))
      ) {
        return previous;
      }
      return next;
    });
  }, [pdfDocument.numPages]);

  // Scroll only when the reader asks for a page. Updating the URL while
  // scrolling must not scroll the reader again.
  useEffect(() => {
    if (!ready) {
      return;
    }
    const container = scrollRef.current;
    const target = Math.min(Math.max(scrollTarget, 1), pdfDocument.numPages);
    const element = pageRefs.current[target - 1];
    if (container === null || element === null || element === undefined) {
      return;
    }

    element.scrollIntoView({ block: "start" });
    measure();
    const frame = window.requestAnimationFrame(() => measure());
    return () => window.cancelAnimationFrame(frame);
    // `scrollTarget` is read at the moment the token changes on purpose.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, scrollToken, measure, pdfDocument.numPages]);

  useEffect(() => {
    if (!ready) {
      return;
    }
    const container = scrollRef.current;
    if (container === null) {
      return;
    }

    let frame = 0;
    const handleScroll = () => {
      if (frame !== 0) {
        return;
      }
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        measure();
      });
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    measure();
    return () => {
      container.removeEventListener("scroll", handleScroll);
      if (frame !== 0) {
        window.cancelAnimationFrame(frame);
      }
    };
  }, [ready, measure]);

  return (
    <div
      ref={scrollRef}
      data-testid="pdf-scroll"
      role="region"
      aria-label={t.knowledge.scrollView}
      tabIndex={0}
      className="h-full overflow-y-auto overflow-x-hidden bg-muted/40 px-4 py-6 outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-inset"
    >
      {failed ? (
        <p className="text-sm text-muted-foreground" role="alert">
          {t.knowledge.pdfError}
        </p>
      ) : (
        <div className="mx-auto flex w-full max-w-3xl flex-col items-center gap-5">
          {Array.from({ length: pdfDocument.numPages }, (_, index) => {
            const pageNumber = index + 1;
            const size = sizes[index];
            return (
              <div
                key={pageNumber}
                ref={(element) => {
                  pageRefs.current[index] = element;
                }}
                data-page={pageNumber}
                className="w-full scroll-mt-6"
              >
                <div
                  className="w-full overflow-hidden rounded-sm bg-white shadow-sm"
                  style={{
                    aspectRatio: size ? `${size.width} / ${size.height}` : "3 / 4",
                  }}
                >
                  {rendered.has(pageNumber) ? (
                    <PdfPageCanvas
                      pdfDocument={pdfDocument}
                      page={pageNumber}
                      label={labelFor(pageNumber)}
                      fit="scroll"
                    />
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Render a PDF in one of two reading modes: a single page that the toolbar
 * turns, or a continuous column the reader scrolls.
 */
export function PdfViewer({
  data,
  mode,
  page,
  scrollToken,
  scrollTarget,
  onVisiblePage,
  labelFor,
}: {
  data: ArrayBuffer | null;
  mode: "page" | "scroll";
  page: number;
  scrollToken: number;
  scrollTarget: number;
  onVisiblePage: (page: number) => void;
  labelFor: (page: number) => string;
}) {
  const t = useT();
  const { pdfDocument, failed } = usePdfDocument(data);

  if (data === null || (pdfDocument === null && !failed)) {
    return (
      <p className="p-6 text-sm text-muted-foreground" role="status">
        {t.knowledge.loadingPdf}
      </p>
    );
  }
  if (pdfDocument === null) {
    return (
      <p className="p-6 text-sm text-muted-foreground" role="alert">
        {t.knowledge.pdfError}
      </p>
    );
  }

  if (mode === "scroll") {
    return (
      <PdfScrollView
        pdfDocument={pdfDocument}
        page={page}
        scrollToken={scrollToken}
        scrollTarget={scrollTarget}
        onVisiblePage={onVisiblePage}
        labelFor={labelFor}
      />
    );
  }

  return (
    <div className="h-full overflow-auto p-4">
      <PdfPageCanvas
        pdfDocument={pdfDocument}
        page={Math.min(page, pdfDocument.numPages)}
        label={labelFor(page)}
        fit="page"
      />
    </div>
  );
}
