import { memo } from "react";
import { Link } from "react-router";

import { SourceThumbnail } from "@/components/chat/source-thumbnail";
import { Badge } from "@/components/ui/badge";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemSeparator,
  ItemTitle,
} from "@/components/ui/item";
import { format, useT } from "@/lib/i18n";
import type { CitationSource } from "@/lib/types";

export interface SourceTarget {
  href: string;
  /** True for a web page, which opens in a new tab. */
  external: boolean;
}

/** The destination of a source row and its markers, shared by both. */
export function sourceTarget(source: CitationSource): SourceTarget | null {
  if (source.kind === "course") {
    if (
      source.doc_id === null ||
      source.doc_id === undefined ||
      source.page_no == null
    ) {
      return null;
    }
    return {
      href: `/knowledge/docs/${encodeURIComponent(source.doc_id)}?page=${source.page_no}`,
      external: false,
    };
  }
  if (source.url === null || source.url === undefined) {
    return null;
  }
  try {
    const url = new URL(source.url);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return { href: source.url, external: true };
  } catch {
    return null;
  }
}

function webHost(source: CitationSource): string {
  if (source.url === null || source.url === undefined) {
    return "";
  }
  try {
    return new URL(source.url).hostname;
  } catch {
    return "";
  }
}

function SourceItemView({ source }: { source: CitationSource }) {
  const t = useT();
  const title = source.title;
  const summary = source.summary.trim() || t.chat.sourceNoSummary;
  const meta =
    source.kind === "course"
      ? format(t.chat.sourceCourseMeta, { page: source.page_no ?? 1 })
      : format(t.chat.sourceWebMeta, { host: webHost(source) });

  const content = (
    <>
      <ItemMedia variant="image" className="self-start">
        <SourceThumbnail source={source} size="lg" />
      </ItemMedia>
      <ItemContent className="min-w-0 gap-0.5">
        <ItemTitle className="w-full">{title}</ItemTitle>
        <ItemDescription className="line-clamp-2">{summary}</ItemDescription>
        <p className="text-[0.7rem] leading-normal text-muted-foreground">
          {meta}
        </p>
      </ItemContent>
      <ItemActions className="self-start">
        <Badge variant="outline" className="font-mono tabular-nums">
          {source.marker}
        </Badge>
      </ItemActions>
    </>
  );

  const target = sourceTarget(source);
  if (target === null) {
    return (
      <Item size="sm" className="flex-nowrap items-start gap-2.5 px-2 py-2">
        {content}
      </Item>
    );
  }
  if (target.external) {
    return (
      <Item
        asChild
        size="sm"
        className="flex-nowrap items-start gap-2.5 rounded-lg px-2 py-2"
      >
        <a href={target.href} target="_blank" rel="noopener noreferrer">
          {content}
        </a>
      </Item>
    );
  }
  return (
    <Item
      asChild
      size="sm"
      className="flex-nowrap items-start gap-2.5 rounded-lg px-2 py-2"
    >
      <Link to={target.href}>{content}</Link>
    </Item>
  );
}

export const SourceItem = memo(SourceItemView);

function SourceListView({ sources }: { sources: CitationSource[] }) {
  return (
    <ItemGroup className="gap-0">
      {sources.map((source, index) => (
        <li
          key={`${source.kind}:${source.marker}`}
          className="source-row-enter list-none"
          style={{ animationDelay: `${Math.min(index, 8) * 30}ms` }}
        >
          {index > 0 ? <ItemSeparator /> : null}
          <SourceItem source={source} />
        </li>
      ))}
    </ItemGroup>
  );
}

export const SourceList = memo(SourceListView);
