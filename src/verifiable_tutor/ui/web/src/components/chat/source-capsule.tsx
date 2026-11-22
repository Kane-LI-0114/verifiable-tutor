import { memo, useMemo } from "react";

import { SourceThumbnail } from "@/components/chat/source-thumbnail";
import {
  AvatarGroup,
  AvatarGroupCount,
} from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { sourceSummaryLabel } from "@/lib/chat/source-summary";
import { useT } from "@/lib/i18n";
import type { CitationSource } from "@/lib/types";

const PREVIEW_THUMBNAILS = 3;

function SourceCapsuleView({
  sources,
  open,
  onToggle,
}: {
  sources: CitationSource[];
  open: boolean;
  onToggle: () => void;
}) {
  const t = useT();
  const previews = useMemo(
    () => sources.slice(0, PREVIEW_THUMBNAILS),
    [sources],
  );
  const extra = sources.length - previews.length;
  const label = useMemo(() => sourceSummaryLabel(sources, t), [sources, t]);

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="h-8 gap-2 rounded-full py-0 pr-2.5 pl-1.5 font-normal"
      aria-label={`${t.chat.openSources}: ${label}`}
      aria-expanded={open}
      aria-controls="source-pane"
      onClick={onToggle}
    >
      <AvatarGroup>
        {previews.map((source) => (
          <SourceThumbnail
            key={`${source.kind}:${source.marker}`}
            source={source}
          />
        ))}
        {extra > 0 ? (
          <AvatarGroupCount className="size-6 text-[0.65rem]">
            +{extra}
          </AvatarGroupCount>
        ) : null}
      </AvatarGroup>
      <span className="text-xs tabular-nums">{label}</span>
    </Button>
  );
}

export const SourceCapsule = memo(SourceCapsuleView);
