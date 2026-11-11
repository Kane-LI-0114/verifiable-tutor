import { memo, useMemo } from "react";

import { SourceThumbnail } from "@/components/chat/source-thumbnail";
import {
  AvatarGroup,
  AvatarGroupCount,
} from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { format, useT } from "@/lib/i18n";
import type { Messages } from "@/lib/i18n/en";
import type { CitationSource } from "@/lib/types";

const PREVIEW_THUMBNAILS = 3;
const COURSE = "course";

type SourceCountKey =
  | "sourceCourseCount"
  | "sourceCourseCountOne"
  | "sourceWebCount"
  | "sourceWebCountOne";

function countLabel(
  t: Messages,
  count: number,
  many: SourceCountKey,
  one: SourceCountKey,
): string {
  return format(t.chat[count === 1 ? one : many], { count });
}

function summaryLabel(sources: CitationSource[], t: Messages): string {
  const course = sources.filter((source) => source.kind === COURSE).length;
  const web = sources.length - course;
  const parts: string[] = [];
  if (course > 0) {
    parts.push(
      countLabel(t, course, "sourceCourseCount", "sourceCourseCountOne"),
    );
  }
  if (web > 0) {
    parts.push(countLabel(t, web, "sourceWebCount", "sourceWebCountOne"));
  }
  return parts.join(" · ");
}

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
  const label = useMemo(() => summaryLabel(sources, t), [sources, t]);

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
