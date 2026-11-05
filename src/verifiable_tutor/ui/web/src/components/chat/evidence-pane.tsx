import { EvidencePanel } from "@/components/chat/evidence-panel";
import {
  readCollapsed,
  SidePane,
  writeCollapsed,
} from "@/components/layout/side-pane";
import { useT } from "@/lib/i18n";
import type { Citation } from "@/lib/types";

export const EVIDENCE_DEFAULT_WIDTH = 380;
export const EVIDENCE_MIN_WIDTH = 280;
export const EVIDENCE_MAX_WIDTH = 640;
export const EVIDENCE_RAIL_WIDTH = 44;
export const EVIDENCE_WIDTH_KEY = "vt.evidence.width";
export const EVIDENCE_COLLAPSED_KEY = "vt.evidence.collapsed";

/** The pane may take at most 55 percent of the viewport, and never more than 640px. */
export function evidenceWidthLimit(): number {
  if (typeof window === "undefined") {
    return EVIDENCE_MAX_WIDTH;
  }
  return Math.min(EVIDENCE_MAX_WIDTH, Math.floor(window.innerWidth * 0.55));
}

/** Read the persisted collapse state. Storage can be blocked, so failures fall back. */
export function readEvidenceCollapsed(): boolean {
  return readCollapsed(EVIDENCE_COLLAPSED_KEY);
}

/** Persist the collapse state. Storage can be blocked, so failures are ignored. */
export function writeEvidenceCollapsed(collapsed: boolean): void {
  writeCollapsed(EVIDENCE_COLLAPSED_KEY, collapsed);
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

  return (
    <SidePane
      testId="evidence-pane"
      label={t.a11y.evidence}
      collapsedLabel={t.a11y.evidenceCollapsed}
      collapseLabel={t.chat.evidenceCollapse}
      expandLabel={t.chat.evidenceExpand}
      resizeLabel={t.chat.evidenceResize}
      widthKey={EVIDENCE_WIDTH_KEY}
      collapsedKey={EVIDENCE_COLLAPSED_KEY}
      collapsed={collapsed}
      onCollapsedChange={onCollapsedChange}
      header={t.chat.evidenceTitle}
      className={className}
      defaultWidth={EVIDENCE_DEFAULT_WIDTH}
      minWidth={EVIDENCE_MIN_WIDTH}
      maxWidth={EVIDENCE_MAX_WIDTH}
      railWidth={EVIDENCE_RAIL_WIDTH}
    >
      <EvidencePanel
        citations={citations}
        activeIndex={activeIndex}
        onSelect={onSelect}
        className="min-h-0 flex-1"
      />
    </SidePane>
  );
}
