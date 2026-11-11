import { FileTextIcon, XIcon } from "lucide-react";
import { memo } from "react";

import { SourceList } from "@/components/chat/source-list";
import { Badge } from "@/components/ui/badge";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { SidePane } from "@/components/layout/side-pane";
import { format, useT } from "@/lib/i18n";
import type { CitationSource } from "@/lib/types";

export const SOURCE_PANE_WIDTH_KEY = "vt.sources.width";
export const SOURCE_PANE_DEFAULT_WIDTH = 380;
export const SOURCE_PANE_MIN_WIDTH = 280;
export const SOURCE_PANE_MAX_WIDTH = 640;

function SourcePaneView({
  sources,
  open = true,
  turnId = null,
  onClose,
  className,
}: {
  sources: CitationSource[];
  open?: boolean;
  turnId?: string | null;
  onClose: () => void;
  className?: string;
}) {
  const t = useT();

  return (
    <SidePane
      id="source-pane"
      testId="source-pane"
      label={t.a11y.sources}
      collapsedLabel={t.a11y.sources}
      collapseLabel={t.chat.closeSources}
      expandLabel={t.chat.openSources}
      resizeLabel={t.chat.sourcesResize}
      widthKey={SOURCE_PANE_WIDTH_KEY}
      open={open}
      closeIcon={<XIcon />}
      collapsed={false}
      onCollapsedChange={(collapsed) => {
        if (collapsed) {
          onClose();
        }
      }}
      header={
        <span className="flex min-w-0 items-center gap-2">
          <span className="truncate">{t.chat.sourcesTitle}</span>
          <Badge variant="secondary" className="tabular-nums">
            {format(t.chat.sourcesCount, { count: sources.length })}
          </Badge>
        </span>
      }
      className={className}
      defaultWidth={SOURCE_PANE_DEFAULT_WIDTH}
      minWidth={SOURCE_PANE_MIN_WIDTH}
      maxWidth={SOURCE_PANE_MAX_WIDTH}
    >
      {sources.length === 0 ? (
        <div className="flex min-h-0 flex-1 items-center justify-center p-6">
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <FileTextIcon />
              </EmptyMedia>
              <EmptyTitle>{t.chat.sourcesEmpty}</EmptyTitle>
              <EmptyDescription>{t.chat.sourcesEmptyBody}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          <SourceList
            key={`${turnId ?? "none"}:${open ? "open" : "closed"}`}
            sources={sources}
          />
        </div>
      )}
    </SidePane>
  );
}

export const SourcePane = memo(SourcePaneView);
