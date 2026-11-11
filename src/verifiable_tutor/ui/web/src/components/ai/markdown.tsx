import { cjk } from "@streamdown/cjk";
import { code } from "@streamdown/code";
import { createMathPlugin } from "@streamdown/math";
import { Streamdown } from "streamdown";

import {
  CITATION_COMPONENTS,
  CitationSourceProvider,
  citationRemarkPlugins,
} from "@/components/ai/citation-markers";
import { cn } from "@/lib/utils";
import type { CitationSource } from "@/lib/types";

const math = createMathPlugin({ singleDollarTextMath: true });

export function Markdown({
  children,
  className,
  sources = [],
}: {
  children: string;
  className?: string;
  sources?: CitationSource[];
}) {
  const stream = (
    <Streamdown
      className={cn("text-sm leading-relaxed", className)}
      plugins={{ code, math, cjk }}
      {...(sources.length > 0
        ? {
            components: CITATION_COMPONENTS,
            remarkPlugins: citationRemarkPlugins,
          }
        : {})}
    >
      {children}
    </Streamdown>
  );

  if (sources.length === 0) {
    return stream;
  }
  return (
    <CitationSourceProvider sources={sources}>{stream}</CitationSourceProvider>
  );
}
