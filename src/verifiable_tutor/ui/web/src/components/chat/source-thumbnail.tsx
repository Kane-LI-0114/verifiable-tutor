import { FileTextIcon, GlobeIcon } from "lucide-react";

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar";
import { useOptionalPreview } from "@/lib/preview/context";
import type { CitationSource } from "@/lib/types";

/** Local page image for a course source; the source site's icon for a web page. */
export function sourceThumbnailUrl(source: CitationSource): string | undefined {
  if (source.kind === "course") {
    if (source.doc_id === null || source.doc_id === undefined || source.page_no == null) {
      return undefined;
    }
    return `/api/corpus/${encodeURIComponent(source.doc_id)}/pages/${source.page_no}.webp`;
  }
  if (source.url === null || source.url === undefined) {
    return undefined;
  }
  try {
    const url = new URL(source.url);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return undefined;
    }
    return `${url.origin}/favicon.ico`;
  } catch {
    return undefined;
  }
}

export function SourceThumbnail({
  source,
  size = "sm",
  className,
}: {
  source: CitationSource;
  size?: "sm" | "lg";
  className?: string;
}) {
  const preview = useOptionalPreview()?.isPreview ?? false;
  const src = preview ? undefined : sourceThumbnailUrl(source);
  const Icon = source.kind === "course" ? FileTextIcon : GlobeIcon;

  return (
    <Avatar size={size} className={className}>
      {src === undefined ? null : (
        <AvatarImage
          src={src}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
        />
      )}
      <AvatarFallback>
        <Icon aria-hidden="true" />
      </AvatarFallback>
    </Avatar>
  );
}
