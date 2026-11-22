import { createContext, useContext, useMemo, type ComponentType, type ReactNode } from "react";
import { SourceItem, sourceTarget } from "@/components/chat/source-list";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Link } from "react-router";
import {
  defaultComponents,
  defaultRemarkPlugins,
  type Components,
} from "streamdown";

import { format, useT } from "@/lib/i18n";
import type { CitationSource } from "@/lib/types";

const CITATION_PREFIX = "#cite-";
const CITATION_MARKER = /\[ref_(\d{1,3})\]/gi;

interface MarkdownNode {
  type: string;
  value?: string;
  url?: string;
  children?: MarkdownNode[];
}

interface CitationSourceValue {
  sources: Map<number, CitationSource>;
}

const CitationSourceContext = createContext<CitationSourceValue | null>(null);

export function CitationSourceProvider({
  sources,
  children,
}: {
  sources: CitationSource[];
  children: ReactNode;
}) {
  const value = useMemo<CitationSourceValue>(
    () => ({
      sources: new Map(sources.map((source) => [source.marker, source])),
    }),
    [sources],
  );
  return (
    <CitationSourceContext.Provider value={value}>
      {children}
    </CitationSourceContext.Provider>
  );
}

function splitMarkers(value: string): MarkdownNode[] {
  const nodes: MarkdownNode[] = [];
  let cursor = 0;
  for (const match of value.matchAll(CITATION_MARKER)) {
    const index = match.index ?? 0;
    if (index > cursor) {
      nodes.push({ type: "text", value: value.slice(cursor, index) });
    }
    nodes.push({
      type: "link",
      url: `${CITATION_PREFIX}${match[1]}`,
      children: [{ type: "text", value: match[0] }],
    });
    cursor = index + match[0].length;
  }
  if (cursor < value.length) {
    nodes.push({ type: "text", value: value.slice(cursor) });
  }
  return nodes.length > 0 ? nodes : [{ type: "text", value }];
}

function walk(node: MarkdownNode, insideLink: boolean): void {
  if (node.children === undefined) {
    return;
  }
  const next: MarkdownNode[] = [];
  let changed = false;
  for (const child of node.children) {
    if (child.type === "text" && !insideLink && child.value !== undefined) {
      const parts = splitMarkers(child.value);
      if (parts.some((part) => part.type === "link")) {
        next.push(...parts);
        changed = true;
        continue;
      }
    }
    walk(child, insideLink || child.type === "link");
    next.push(child);
  }
  if (changed) {
    node.children = next;
  }
}

/** Turn `[ref_n]` text into marker links that the renderer resolves to a source. */
export function remarkCitationMarkers() {
  return (tree: MarkdownNode): void => {
    walk(tree, false);
  };
}

function markerFromHref(href: string | undefined): number | null {
  if (href === undefined || !href.startsWith(CITATION_PREFIX)) {
    return null;
  }
  const marker = Number(href.slice(CITATION_PREFIX.length));
  return Number.isInteger(marker) && marker > 0 ? marker : null;
}

const MARKER_CLASS =
  "mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-md border border-border bg-muted/50 px-1 align-baseline font-mono text-[11px] tabular-nums leading-none text-foreground no-underline transition-colors hover:border-foreground/30 hover:bg-muted focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none";

const DefaultLink = defaultComponents.a as ComponentType<
  Record<string, unknown>
>;

/**
 * Streamdown's `a` renderer. Citation links become source links; every other
 * link keeps Streamdown's own renderer, including its link-safety treatment.
 */
export function CitationMarkerLink({
  href,
  children,
  ...props
}: {
  href?: string;
  children?: ReactNode;
  [key: string]: unknown;
}) {
  const t = useT();
  const value = useContext(CitationSourceContext);
  const marker = markerFromHref(href);
  const source = marker === null ? undefined : value?.sources.get(marker);
  const label =
    source === undefined
      ? undefined
      : format(t.chat.citationMarker, {
          marker: source.marker,
          title: source.title,
        });

  if (marker !== null && source === undefined) {
    return <>{children}</>;
  }

  if (source === undefined) {
    return (
      <DefaultLink href={href} {...props}>
        {children}
      </DefaultLink>
    );
  }

  const target = sourceTarget(source);
  if (target === null) {
    return <>{children}</>;
  }
  const markerLink = target.external ? (
    <a
      href={target.href}
      className={MARKER_CLASS}
      aria-label={label}
      target="_blank"
      rel="noopener noreferrer"
    >
      {source.marker}
    </a>
  ) : (
    <Link to={target.href} className={MARKER_CLASS} aria-label={label}>
      {source.marker}
    </Link>
  );
  return (
    <HoverCard>
      <HoverCardTrigger asChild>{markerLink}</HoverCardTrigger>
      <HoverCardContent align="start" className="w-80 p-1.5" sideOffset={6}>
        <SourceItem source={source} />
      </HoverCardContent>
    </HoverCard>
  );
}

const CITATION_COMPONENTS = { a: CitationMarkerLink } as Components;

/** The remark plugins a citation-enabled Markdown render needs. */
export const citationRemarkPlugins = [
  ...Object.values(defaultRemarkPlugins),
  remarkCitationMarkers,
];

export { CITATION_COMPONENTS };
