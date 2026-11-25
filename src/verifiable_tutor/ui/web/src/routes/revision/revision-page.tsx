import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDownIcon,
  ChevronRightIcon,
  Loader2Icon,
} from "lucide-react";

import { PageEmpty, PageError, PageHeader } from "@/components/layout/page-states";
import {
  getRevisionTree,
  type RevisionCategory,
  type RevisionTheme,
} from "@/lib/api/revision";
import { useT } from "@/lib/i18n";

const CATEGORY_DOT: Record<RevisionCategory, string> = {
  assignment: "bg-red-500",
  lecture: "bg-blue-600",
  tutorial: "bg-blue-400",
  other: "bg-slate-400",
};

const PAD = 32;
const COL_ROOT = 0;
const W_ROOT = 220;
const H_ROOT = 64;
const COL_THEME = 280;
const W_THEME = 560;
const H_THEME_DEFAULT = 120;
const COL_DOC = COL_THEME + 72;
const W_DOC = 460;
const H_DOC = 44;
const GAP_DOC = 10;
const GAP_THEME = 28;

interface DocumentNode {
  doc_id: string;
  title: string | null;
  category: RevisionCategory;
  y: number;
}

interface ThemeNode {
  theme: RevisionTheme;
  height: number;
  y: number;
  documents: DocumentNode[];
}

interface MapLayout {
  width: number;
  height: number;
  rootY: number;
  themes: ThemeNode[];
}

function layoutMap(
  themes: RevisionTheme[],
  collapsed: Set<string>,
  heights: Record<string, number>,
): MapLayout {
  let cursor = PAD;
  const rows: ThemeNode[] = themes.map((theme) => {
    const height = heights[theme.id] ?? H_THEME_DEFAULT;
    const y = cursor + height / 2;
    const documents = collapsed.has(theme.id) ? [] : theme.documents;
    const docsTop = cursor + height + 14;
    const placed = documents.map((document, index) => ({
      doc_id: document.doc_id,
      title: document.title,
      category: document.category,
      y: docsTop + index * (H_DOC + GAP_DOC) + H_DOC / 2,
    }));
    const blockBottom = documents.length
      ? docsTop + documents.length * (H_DOC + GAP_DOC) - GAP_DOC
      : cursor + height;
    cursor = blockBottom + GAP_THEME;
    return { theme, height, y, documents: placed };
  });
  const rootY =
    rows.length === 0 ? PAD + H_ROOT / 2 : (rows[0].y + rows[rows.length - 1].y) / 2;
  return {
    width: COL_THEME + W_THEME + PAD,
    height: Math.max(cursor - GAP_THEME + PAD, PAD * 2 + H_ROOT),
    rootY,
    themes: rows,
  };
}

function curve(x1: number, y1: number, x2: number, y2: number): string {
  const bend = Math.max((x2 - x1) / 2, 24);
  return `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;
}

export function RevisionPage() {
  const t = useT();
  const [themes, setThemes] = useState<RevisionTheme[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [heights, setHeights] = useState<Record<string, number>>({});
  const themeRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  function load() {
    setStatus("loading");
    getRevisionTree()
      .then((body) => {
        setThemes(body.themes);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useLayoutEffect(() => {
    setHeights((current) => {
      let changed = false;
      const next = { ...current };
      for (const theme of themes) {
        const element = themeRefs.current[theme.id];
        if (element && Math.abs((next[theme.id] ?? 0) - element.offsetHeight) > 0.5) {
          next[theme.id] = element.offsetHeight;
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [themes, collapsed]);

  function toggle(themeId: string) {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(themeId)) {
        next.delete(themeId);
      } else {
        next.add(themeId);
      }
      return next;
    });
  }

  const map = useMemo(
    () => layoutMap(themes, collapsed, heights),
    [themes, collapsed, heights],
  );

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl space-y-4 p-6">
        <PageHeader title={t.revision.title} description={t.revision.subtitle} />

        {status === "loading" ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <Loader2Icon className="size-6 animate-spin" />
          </div>
        ) : status === "error" ? (
          <PageError
            title={t.revision.loadError}
            description={t.common.errorBody}
            onRetry={load}
          />
        ) : themes.length === 0 ? (
          <PageEmpty
            title={t.revision.emptyTitle}
            description={t.revision.emptyBody}
          />
        ) : (
          <div className="overflow-auto rounded-xl border bg-muted/20 p-2">
            <div
              className="relative"
              style={{ width: map.width, height: map.height }}
            >
              <svg
                width={map.width}
                height={map.height}
                className="absolute inset-0"
                aria-hidden="true"
              >
                {map.themes.map((node) => (
                  <path
                    key={`${node.theme.id}-root`}
                    d={curve(COL_ROOT + W_ROOT, map.rootY, COL_THEME, node.y)}
                    fill="none"
                    strokeWidth={1.5}
                    className="stroke-slate-300"
                  />
                ))}
                {map.themes.flatMap((node) => {
                  const trunk = COL_THEME + 24;
                  const bottom = node.y + node.height / 2;
                  return node.documents.map((document) => (
                    <path
                      key={`${node.theme.id}-${document.doc_id}`}
                      d={`M ${trunk} ${bottom} L ${trunk} ${document.y} L ${COL_DOC} ${document.y}`}
                      fill="none"
                      strokeWidth={1.5}
                      className="stroke-slate-300"
                    />
                  ));
                })}
              </svg>

              <div
                className="absolute flex flex-col justify-center rounded-xl bg-primary px-4 text-primary-foreground shadow-md"
                style={{
                  left: COL_ROOT,
                  top: map.rootY - H_ROOT / 2,
                  width: W_ROOT,
                  height: H_ROOT,
                }}
              >
                <span className="truncate text-sm font-semibold">
                  {t.app.course}
                </span>
                <span className="truncate text-xs opacity-80">
                  {t.revision.title}
                </span>
              </div>

              {map.themes.map((node) => {
                const isCollapsed = collapsed.has(node.theme.id);
                return (
                  <button
                    key={node.theme.id}
                    ref={(element) => {
                      themeRefs.current[node.theme.id] = element;
                    }}
                    type="button"
                    aria-expanded={!isCollapsed}
                    onClick={() => toggle(node.theme.id)}
                    className="absolute flex items-start gap-2 rounded-lg border bg-background p-4 text-left shadow-sm transition-colors hover:bg-accent/40"
                    style={{
                      left: COL_THEME,
                      top: node.y - node.height / 2,
                      width: W_THEME,
                    }}
                  >
                    {isCollapsed ? (
                      <ChevronRightIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronDownIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block text-base font-semibold">
                        {node.theme.title}
                      </span>
                      <span className="mt-1 block text-sm text-muted-foreground">
                        {node.theme.summary}
                      </span>
                    </span>
                    <span className="shrink-0 rounded-full bg-muted px-1.5 text-xs text-muted-foreground">
                      {node.theme.documents.length}
                    </span>
                  </button>
                );
              })}

              {map.themes.flatMap((node) =>
                node.documents.map((document) => (
                  <div
                    key={document.doc_id}
                    aria-disabled="true"
                    className="absolute flex items-center gap-2 rounded-md border bg-background px-3 shadow-sm"
                    style={{
                      left: COL_DOC,
                      top: document.y - H_DOC / 2,
                      width: W_DOC,
                      height: H_DOC,
                    }}
                  >
                    <span
                      className={`size-2.5 shrink-0 rounded-full ${CATEGORY_DOT[document.category]}`}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 truncate text-sm">
                      {document.title ?? document.doc_id}
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {t.revision.categories[document.category]}
                    </span>
                    <span className="shrink-0 text-[10px] text-muted-foreground">
                      {t.revision.notGenerated}
                    </span>
                  </div>
                )),
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
