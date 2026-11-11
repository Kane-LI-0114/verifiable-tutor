import { PanelRightCloseIcon, PanelRightOpenIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Resizable, collapsible right-hand pane.
 *
 * The chat page shows one answer's source list in it and the knowledge page shows file details
 * or a conversation, so the resize, collapse, persistence, and keyboard
 * mechanics live here once. The caller supplies the labels, the storage keys,
 * and the header content.
 */
export interface SidePaneProps {
  /** Accessible name of the pane when it is open. */
  label: string;
  /** Accessible name of the collapsed rail. */
  collapsedLabel: string;
  collapseLabel: string;
  expandLabel: string;
  resizeLabel: string;
  /** localStorage keys so each page remembers its own width and state. */
  widthKey: string;
  collapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
  /** Header content, shown when the pane is open. */
  header: ReactNode;
  children: ReactNode;
  className?: string;
  testId?: string;
  id?: string;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  railWidth?: number;
}

const RESIZE_STEP = 16;

function clampWidth(
  width: number,
  defaultWidth: number,
  minWidth: number,
  maxWidth: number,
): number {
  const limit =
    typeof window === "undefined"
      ? maxWidth
      : Math.min(maxWidth, Math.floor(window.innerWidth * 0.55));
  const rounded = Number.isFinite(width) ? Math.round(width) : defaultWidth;
  return Math.min(Math.max(rounded, minWidth), limit);
}

function readStoredWidth(key: string, fallback: number): number {
  try {
    const raw = window.localStorage?.getItem(key);
    if (raw === null || raw === undefined) {
      return fallback;
    }
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function storeWidth(key: string, width: number): void {
  try {
    window.localStorage?.setItem(key, String(width));
  } catch {
    // Storage can be blocked; the in-memory width still applies.
  }
}

/** Read a persisted collapse flag; storage failures fall back to open. */
export function readCollapsed(key: string): boolean {
  try {
    return window.localStorage?.getItem(key) === "true";
  } catch {
    return false;
  }
}

/** Persist a collapse flag; storage failures are ignored. */
export function writeCollapsed(key: string, collapsed: boolean): void {
  try {
    window.localStorage?.setItem(key, collapsed ? "true" : "false");
  } catch {
    // The in-memory state still applies for this session.
  }
}

export function SidePane({
  label,
  collapsedLabel,
  collapseLabel,
  expandLabel,
  resizeLabel,
  widthKey,
  collapsed,
  onCollapsedChange,
  header,
  children,
  className,
  testId,
  id,
  defaultWidth = 380,
  minWidth = 280,
  maxWidth = 640,
  railWidth = 44,
}: SidePaneProps) {
  const [width, setWidth] = useState<number>(() =>
    clampWidth(readStoredWidth(widthKey, defaultWidth), defaultWidth, minWidth, maxWidth),
  );
  const [dragging, setDragging] = useState(false);
  const dragOrigin = useRef<{ x: number; width: number } | null>(null);

  const applyWidth = useCallback(
    (next: number) => {
      const clamped = clampWidth(next, defaultWidth, minWidth, maxWidth);
      setWidth(clamped);
      storeWidth(widthKey, clamped);
      return clamped;
    },
    [defaultWidth, maxWidth, minWidth, widthKey],
  );

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

  const limit =
    typeof window === "undefined"
      ? maxWidth
      : Math.min(maxWidth, Math.floor(window.innerWidth * 0.55));

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
      applyWidth(minWidth);
    } else if (event.key === "End") {
      event.preventDefault();
      applyWidth(limit);
    }
  }

  return (
    <aside
      id={id}
      data-testid={testId}
      data-collapsed={collapsed ? "true" : "false"}
      aria-label={collapsed ? collapsedLabel : label}
      className={cn(
        "relative hidden h-full shrink-0 flex-col border-l bg-background lg:flex",
        className,
      )}
      style={{ width: collapsed ? railWidth : width }}
    >
      {collapsed ? (
        <div className="flex h-full flex-col items-center gap-1 py-2">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={expandLabel}
            title={expandLabel}
            onClick={() => onCollapsedChange(false)}
          >
            <PanelRightOpenIcon />
          </Button>
          <span className="mt-1 text-[0.65rem] font-medium tracking-wide text-muted-foreground [writing-mode:vertical-rl]">
            {label}
          </span>
        </div>
      ) : (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label={resizeLabel}
            aria-valuenow={width}
            aria-valuemin={minWidth}
            aria-valuemax={limit}
            tabIndex={0}
            className={cn(
              "absolute top-0 left-0 z-10 h-full w-1.5 -translate-x-1/2 cursor-col-resize touch-none outline-none select-none",
              "hover:bg-primary/20 focus-visible:bg-primary/30",
              dragging && "bg-primary/40",
            )}
            onDoubleClick={() => applyWidth(defaultWidth)}
            onKeyDown={onKeyDown}
            onPointerDown={startDrag}
          />
          <div className="flex items-center gap-2 border-b px-3 py-2">
            <span className="truncate text-sm font-medium">{header}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="ml-auto"
              aria-label={collapseLabel}
              title={collapseLabel}
              onClick={() => onCollapsedChange(true)}
            >
              <PanelRightCloseIcon />
            </Button>
          </div>
          {children}
        </>
      )}
    </aside>
  );
}
