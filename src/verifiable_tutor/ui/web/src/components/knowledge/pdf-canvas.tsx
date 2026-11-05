import { useEffect, useRef, useState } from "react";

import { useT } from "@/lib/i18n";

type PdfModule = {
  GlobalWorkerOptions: { workerSrc: string };
  getDocument: (options: { data: ArrayBuffer }) => {
    promise: Promise<{
      numPages: number;
      getPage: (page: number) => Promise<{
        getViewport: (options: { scale: number }) => { width: number; height: number };
        render: (options: Record<string, unknown>) => { promise: Promise<void> };
      }>;
    }>;
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
 * Render one page of a PDF on a canvas.
 *
 * The whole file is fetched once by the caller; this component only re-renders
 * when the page changes. A failure is reported in place instead of leaving a
 * blank frame.
 */
export function PdfCanvas({
  data,
  page,
  label,
}: {
  data: ArrayBuffer | null;
  page: number;
  label: string;
}) {
  const t = useT();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (data === null) {
      return;
    }
    let cancelled = false;
    setFailed(false);

    async function render() {
      try {
        const pdfjs = await loadPdf();
        const document = await pdfjs.getDocument({ data: data!.slice(0) }).promise;
        const pdfPage = await document.getPage(Math.min(page, document.numPages));
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
  }, [data, page]);

  if (data === null) {
    return (
      <p className="p-6 text-sm text-muted-foreground" role="status">
        {t.knowledge.loadingPdf}
      </p>
    );
  }
  if (failed) {
    return (
      <p className="p-6 text-sm text-muted-foreground" role="alert">
        {t.knowledge.pdfError}
      </p>
    );
  }
  return (
    <canvas
      ref={canvasRef}
      aria-label={label}
      className="mx-auto max-h-full max-w-full rounded-sm bg-white shadow-sm"
    />
  );
}
