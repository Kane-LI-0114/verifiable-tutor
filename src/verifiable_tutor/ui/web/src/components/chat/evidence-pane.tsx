import { PanelRightCloseIcon, PanelRightOpenIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { EvidencePanel } from "@/components/chat/evidence-panel";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

export const EVIDENCE_DEFAULT_WIDTH = 380;
export const EVIDENCE_MIN_WIDTH = 280;
export const EVIDENCE_MAX_WIDTH = 640;
export const EVIDENCE_RAIL_WIDTH = 44;
export const EVIDENCE_WIDTH_KEY = "vt.evidence.width";
export const EVIDENCE_COLLAPSED_KEY = "vt.evidence.collapsed";

const RESIZE_STEP = 16;

/** The pane may take at most 55 percent of the viewport, and never more than 640px. */
export function evidenceWidthLimit(): number {
  if (typeof window === "undefined") {
    return EVIDENCE_MAX_WIDTH;
  }
  return Math.min(EVIDENCE_MAX_WIDTH, Math.floor(window.innerWidth * 0.55));
}

function clampWidth(width: number): number {
  const limit = evidenceWidthLimit();
  const rounded = Number.isFinite(width) ? Math.round(width) : EVIDENCE_DEFAULT_WIDTH;
  return Math.min(Math.max(rounded, EVIDENCE_MIN_WIDTH), limit);
}

function readStoredWidth(): number {
  try {
    const raw = window.localStorage?.getItem(EVIDENCE_WIDTH_KEY);
    if (raw === null || raw === undefined) {
      return EVIDENCE_DEFAULT_WIDTH;
    }
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) {
      return EVIDENCE_DEFAULT_WIDTH;
    }
    return clampWidth(parsed);
  } catch {
    return EVIDENCE_DEFAULT_WIDTH;
  }
}

function storeWidth(width: number): void {
  try {
    window.localStorage?.setItem(EVIDENCE_WIDTH_KEY, String(width));
  } catch {
    // Storage can be blocked; the in-memory width still applies.
  }
}

/** Read the persisted collapse state. Storage can be blocked, so failures fall back. */
export function readEvidenceCollapsed(): boolean {
  try {
    return window.localStorage?.getItem(EVIDENCE_COLLAPSED_KEY) === "true";
  } catch {
    return false;
  }
}

/** Persist the collapse state. Storage can be blocked, so failures are ignored. */
export function writeEvidenceCollapsed(collapsed: boolean): void {
  try {
    window.localStorage?.setItem(
      EVIDENCE_COLLAPSED_KEY,
      collapsed ? "true" : "false",
    );
  } catch {
    // The in-memory state still applies for this session.
  }
}

export function EvidencePane({
  citations,
  activeIndex,
  onSelect,
  collapsed,
  onCollapsedChange,
  className,
}: {
  citations: Citation[];
  activeIndex: number | null;
  onSelect: (index: number) => void;
  collapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
  className?: string;
}) {
  const t = useT();
  const [width, setWidth] = useState<number>(() => readStoredWidth());
  const [dragging, setDragging] = useState(false);
  const dragOrigin = useRef<{ x: number; width: number } | null>(null);

  const applyWidth = useCallback((next: number) => {
    const clamped = clampWidth(next);
    setWidth(clamped);
    storeWidth(clamped);
    return clamped;
  }, []);

  useEffect(() => {
    if (!dragging) {
      return;
    }

    function onPointerMove(event: PointerEvent) {
      if (dragOrigin.current === null) {
        return;
      }
      applyWidth(dragOrigin.current.width + (dragOrigin.current.x - event.clientX));
    }

    function stopDrag() {
      dragOrigin.current = null;
      setDragging(false);
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDrag);
    window.addEventListener("pointercancel", stopDrag);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopDrag);
      window.removeEventListener("pointercancel", stopDrag);
    };
  }, [applyWidth, dragging]);

  const limit = evidenceWidthLimit();

  function startDrag(event: React.PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    dragOrigin.current = { x: event.clientX, width };
    setDragging(true);
    try {
      event.currentTarget.setPointerCapture?.(event.pointerId);
    } catch {
      // Pointer capture is optional; the window listeners still track the drag.
    }
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      applyWidth(width + RESIZE_STEP);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      applyWidth(width - RESIZE_STEP);
    } else if (event.key === "Home") {
      event.preventDefault();
      applyWidth(EVIDENCE_MIN_WIDTH);
    } else if (event.key === "End") {
      event.preventDefault();
      applyWidth(limit);
    }
  }

  return (
    <aside
      data-testid="evidence-pane"
      data-collapsed={collapsed ? "true" : "false"}
      aria-label={collapsed ? t.a11y.evidenceCollapsed : t.a11y.evidence}
      className={cn(
        "relative hidden h-full shrink-0 flex-col border-l bg-background lg:flex",
        className,
      )}
      style={{ width: collapsed ? EVIDENCE_RAIL_WIDTH : width }}
    >
      {collapsed ? (
        <div className="flex h-full flex-col items-center gap-1 py-2">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={t.chat.evidenceExpand}
            title={t.chat.evidenceExpand}
            onClick={() => onCollapsedChange(false)}
          >
            <PanelRightOpenIcon />
          </Button>
          <span className="mt-1 text-[0.65rem] font-medium uppercase tracking-wide text-muted-foreground [writing-mode:vertical-rl]">
            {t.chat.evidenceTitle}
          </span>
        </div>
      ) : (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label={t.chat.evidenceResize}
            aria-valuenow={width}
            aria-valuemin={EVIDENCE_MIN_WIDTH}
            aria-valuemax={limit}
            tabIndex={0}
            className={cn(
              "absolute top-0 left-0 z-10 h-full w-1.5 -translate-x-1/2 cursor-col-resize touch-none outline-none select-none",
              "hover:bg-primary/20 focus-visible:bg-primary/30",
              dragging && "bg-primary/40",
            )}
            onDoubleClick={() => applyWidth(EVIDENCE_DEFAULT_WIDTH)}
            onKeyDown={onKeyDown}
            onPointerDown={startDrag}
          />
          <div className="flex items-center gap-2 border-b px-3 py-2">
            <span className="truncate text-sm font-medium">
              {t.chat.evidenceTitle}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="ml-auto"
              aria-label={t.chat.evidenceCollapse}
              title={t.chat.evidenceCollapse}
              onClick={() => onCollapsedChange(true)}
            >
              <PanelRightCloseIcon />
            </Button>
          </div>
          <EvidencePanel
            citations={citations}
            activeIndex={activeIndex}
            onSelect={onSelect}
            className="min-h-0 flex-1"
          />
        </>
      )}
    </aside>
  );
}
