import { BookOpenIcon, ExternalLinkIcon, SearchIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { EvidencePanel } from "@/components/chat/evidence-panel";
import { PageEmpty, PageError, PageHeader, PageLoading } from "@/components/layout/page-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { format, useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";
import { PREVIEW_KNOWLEDGE_CARDS } from "@/lib/preview/fixtures";
import type { Citation, KnowledgeCard } from "@/lib/types";

function totalCitations(card: KnowledgeCard): number {
  return card.citations.length;
}

export function KnowledgePage() {
  const t = useT();
  const navigate = useNavigate();
  const { pageState } = usePreview();
  const [query, setQuery] = useState("");
  const [docFilter, setDocFilter] = useState("all");
  const [selected, setSelected] = useState<KnowledgeCard | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const documents = useMemo(
    () => Array.from(new Set(PREVIEW_KNOWLEDGE_CARDS.map((card) => card.doc_id))),
    [],
  );

  const cards = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return PREVIEW_KNOWLEDGE_CARDS.filter((card) => {
      const matchesDoc = docFilter === "all" || card.doc_id === docFilter;
      const haystack = [
        card.summary,
        ...card.key_terms,
        ...card.study_questions,
        card.section ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return matchesDoc && (needle.length === 0 || haystack.includes(needle));
    });
  }, [docFilter, query]);

  const activeCitations = selected?.citations ?? [];
  const activeIndex =
    activeCitation === null
      ? null
      : Math.max(activeCitations.indexOf(activeCitation), 0);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-4 p-6">
        <PageHeader title={t.knowledge.title} description={t.knowledge.subtitle} />

        <div className="flex flex-col gap-2 sm:flex-row">
          <InputGroup className="sm:max-w-md">
            <InputGroupAddon>
              <SearchIcon />
            </InputGroupAddon>
            <InputGroupInput
              aria-label={t.knowledge.searchTitle}
              placeholder={t.knowledge.searchPlaceholder}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </InputGroup>
          <Select value={docFilter} onValueChange={setDocFilter}>
            <SelectTrigger aria-label={t.knowledge.docFilter}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t.knowledge.allDocuments}</SelectItem>
              {documents.map((doc) => (
                <SelectItem key={doc} value={doc}>
                  {doc}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Badge variant="secondary" className="h-8 self-start px-3">
            {format(cards.length === 1 ? t.knowledge.totalOne : t.knowledge.total, {
              count: cards.length,
            })}
          </Badge>
        </div>

        {pageState === "loading" ? (
          <PageLoading label={t.knowledge.loading} />
        ) : pageState === "error" ? (
          <PageError title={t.common.errorTitle} description={t.common.errorBody} />
        ) : pageState === "empty" ? (
          <PageEmpty
            title={t.common.emptyTitle}
            description={t.common.emptyBody}
          />
        ) : cards.length === 0 ? (
          <PageEmpty
            title={t.knowledge.emptyTitle}
            description={t.knowledge.emptyBody}
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {cards.map((card) => (
              <Card key={card.chunk_id} className="flex flex-col">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      {format(t.knowledge.page, { page: card.page_no })}
                    </Badge>
                    <span className="truncate text-xs text-muted-foreground">
                      {card.doc_id}
                    </span>
                  </div>
                  <CardTitle>
                    <h2 className="text-sm font-semibold">
                      {card.section ?? card.doc_id}
                    </h2>
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 space-y-3">
                  <p className="text-sm text-muted-foreground">{card.summary}</p>
                  <div className="flex flex-wrap gap-1">
                    {card.key_terms.map((term) => (
                      <Badge key={term} variant="secondary">
                        {term}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
                <CardFooter className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                  <span>
                    {t.knowledge.studyQuestions}: {card.study_questions.length} ·{" "}
                    {t.knowledge.citations}: {totalCitations(card)}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelected(card)}
                  >
                    <ExternalLinkIcon />
                    {t.knowledge.openCard}
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        <p className="text-xs text-muted-foreground">{t.knowledge.previewNotice}</p>
      </div>

      <Sheet
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelected(null);
            setActiveCitation(null);
          }
        }}
      >
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>{selected?.section ?? t.knowledge.title}</SheetTitle>
            <SheetDescription>
              {selected
                ? `${selected.doc_id} · ${format(t.knowledge.page, {
                    page: selected.page_no,
                  })}`
                : null}
            </SheetDescription>
          </SheetHeader>
          {selected ? (
            <div className="space-y-4 p-4">
              <p className="text-sm">{selected.summary}</p>
              <section className="space-y-2">
                <h3 className="text-sm font-medium">{t.knowledge.keyTerms}</h3>
                <div className="flex flex-wrap gap-1">
                  {selected.key_terms.map((term) => (
                    <Badge key={term} variant="secondary">
                      {term}
                    </Badge>
                  ))}
                </div>
              </section>
              <section className="space-y-2">
                <h3 className="text-sm font-medium">{t.knowledge.studyQuestions}</h3>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {selected.study_questions.map((question) => (
                    <li key={question}>{question}</li>
                  ))}
                </ul>
              </section>
              <section className="space-y-2">
                <h3 className="text-sm font-medium">{t.knowledge.citations}</h3>
                <ul className="space-y-2">
                  {selected.citations.map((citation, index) => (
                    <li key={`${citation.doc_id}:${citation.page_no}:${index}`}>
                      <button
                        type="button"
                        className="w-full rounded-md border p-2 text-left text-sm hover:bg-muted"
                        onClick={() => setActiveCitation(citation)}
                      >
                        <span className="block text-xs text-muted-foreground">
                          {citation.doc_id} ·{" "}
                          {format(t.knowledge.page, { page: citation.page_no })}
                        </span>
                        {citation.quote}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
              <Button
                type="button"
                onClick={() =>
                  navigate("/chat", {
                    state: {
                      draft: `Build a review outline for ${selected.doc_id} page ${selected.page_no}.`,
                    },
                  })
                }
              >
                <BookOpenIcon />
                {t.knowledge.useInOutline}
              </Button>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>

      <Sheet
        open={activeCitation !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActiveCitation(null);
          }
        }}
      >
        <SheetContent side="left" className="w-full p-0 sm:max-w-lg">
          <SheetHeader className="border-b">
            <SheetTitle>{t.chat.evidenceTitle}</SheetTitle>
          </SheetHeader>
          <EvidencePanel
            citations={activeCitations}
            activeIndex={activeIndex}
            onSelect={(index) => setActiveCitation(activeCitations[index] ?? null)}
            className="min-h-0 flex-1"
          />
        </SheetContent>
      </Sheet>
    </div>
  );
}
