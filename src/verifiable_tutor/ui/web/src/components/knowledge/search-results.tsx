import { FileTextIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { SearchDocument, SearchMatch } from "@/lib/api/knowledge";
import { useT } from "@/lib/i18n";
import { HighlightedText } from "@/lib/knowledge/highlight";

/** The reason a document matched, shown as a short chip. */
function matchLabel(match: SearchMatch): string {
  switch (match.kind) {
    case "filename":
      return "file name";
    case "folder":
      return "folder";
    case "summary":
      return "AI summary";
    case "content":
      return `page ${match.page_no ?? 1}`;
  }
}

/** Search results grouped by document, each row saying why it matched. */
export function SearchResults({
  query,
  documents,
  onOpen,
}: {
  query: string;
  documents: SearchDocument[];
  onOpen: (docId: string) => void;
}) {
  const t = useT();

  if (documents.length === 0) {
    return (
      <div className="rounded-md border border-dashed p-8 text-center">
        <p className="text-sm font-medium">{t.knowledge.noResultsTitle}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {t.knowledge.noResultsBody}
        </p>
      </div>
    );
  }

  return (
    <ul className="space-y-3" aria-label={t.knowledge.searchTitle}>
      {documents.map((document) => (
        <li key={document.id} className="rounded-md border">
          <button
            type="button"
            className="flex w-full items-center gap-2 border-b px-3 py-2 text-left hover:bg-muted/60"
            onClick={() => onOpen(document.id)}
          >
            <FileTextIcon className="size-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-sm font-medium">{document.title}</span>
            <span className="ml-auto shrink-0 text-xs text-muted-foreground">
              {t.knowledge.pages}: {document.page_count}
            </span>
          </button>
          <ul className="divide-y">
            {document.matches.map((match, index) => (
              <li key={`${document.id}-${index}`} className="flex gap-2 px-3 py-2">
                <Badge variant="outline" className="h-5 shrink-0">
                  {matchLabel(match)}
                </Badge>
                <span className="min-w-0 text-sm text-muted-foreground">
                  <HighlightedText text={match.snippet} ranges={match.highlights} />
                </span>
              </li>
            ))}
          </ul>
        </li>
      ))}
      <li className="sr-only">{query}</li>
    </ul>
  );
}
