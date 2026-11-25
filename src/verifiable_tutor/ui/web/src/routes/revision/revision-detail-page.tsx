import { useEffect, useState } from "react";
import { ArrowLeftIcon, Loader2Icon } from "lucide-react";
import { Link, useParams } from "react-router";

import { Markdown } from "@/components/ai/markdown";
import { PageEmpty, PageHeader } from "@/components/layout/page-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import {
  getRevisionDocument,
  revisionMarkdownUrl,
  setRevisionPoint,
  type RevisionDocumentDetail,
  type RevisionPoint,
} from "@/lib/api/revision";
import { format, useT } from "@/lib/i18n";

export function RevisionDetailPage() {
  const t = useT();
  const { docId = "" } = useParams();
  const [detail, setDetail] = useState<RevisionDocumentDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getRevisionDocument(docId)
      .then((body) => {
        if (cancelled) return;
        setDetail(body);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) {
          setError(t.revision.detailLoadError);
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId]);

  async function toggle(point: RevisionPoint, mastered: boolean) {
    setDetail((current) => {
      if (current === null) return current;
      return {
        ...current,
        points: current.points.map((entry) =>
          entry.id === point.id ? { ...entry, mastered } : entry,
        ),
        mastered: current.mastered + (mastered ? 1 : -1),
      };
    });
    try {
      const counts = await setRevisionPoint(point.id, mastered);
      setDetail((current) =>
        current === null ? current : { ...current, mastered: counts.mastered },
      );
    } catch {
      setDetail((current) => {
        if (current === null) return current;
        return {
          ...current,
          points: current.points.map((entry) =>
            entry.id === point.id ? { ...entry, mastered: !mastered } : entry,
          ),
          mastered: current.mastered + (mastered ? -1 : 1),
        };
      });
      setError(t.common.errorBody);
    }
  }

  if (status === "loading") {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-muted-foreground">
        <Loader2Icon className="size-6 animate-spin" />
      </div>
    );
  }

  if (status === "error" || detail === null) {
    return (
      <div className="mx-auto w-full max-w-3xl p-6">
        <PageEmpty
          title={t.revision.detailLoadError}
          description={error ?? t.common.errorBody}
        />
      </div>
    );
  }

  const percent =
    detail.total > 0 ? (detail.mastered / detail.total) * 100 : 0;

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl space-y-5 p-6">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link to="/revision">
            <ArrowLeftIcon />
            {t.revision.back}
          </Link>
        </Button>

        <PageHeader
          title={detail.title ?? detail.doc_id}
          description={detail.theme_title ?? undefined}
        />

        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="secondary">
            {t.revision.categories[detail.category]}
          </Badge>
          <Progress value={percent} className="max-w-48" />
          <span className="text-sm tabular-nums text-muted-foreground">
            {detail.mastered}/{detail.total}
          </span>
          <Button asChild variant="outline" size="sm" className="ml-auto">
            <a href={revisionMarkdownUrl(detail.doc_id)} download>
              {t.revision.download}
            </a>
          </Button>
        </div>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {detail.intro_markdown ? (
          <div className="rounded-lg border bg-background p-5">
            <Markdown className="text-[15px] leading-relaxed">
              {detail.intro_markdown}
            </Markdown>
          </div>
        ) : null}

        <div className="space-y-8">
          {detail.points.map((point) => (
            <section key={point.id} className="space-y-2">
              <div className="flex items-start gap-3">
                <Checkbox
                  id={`point-${point.id}`}
                  className="mt-1"
                  checked={point.mastered}
                  onCheckedChange={(checked) =>
                    void toggle(point, checked === true)
                  }
                />
                <label
                  htmlFor={`point-${point.id}`}
                  className={
                    point.mastered
                      ? "cursor-pointer text-lg font-semibold text-muted-foreground line-through"
                      : "cursor-pointer text-lg font-semibold"
                  }
                >
                  {point.title}
                </label>
              </div>
              <div className="pl-7">
                <Markdown className="text-[15px] leading-relaxed">
                  {point.body_markdown}
                </Markdown>
                {point.page_no !== null ? (
                  <Button asChild variant="link" size="sm" className="px-0">
                    <Link
                      to={`/knowledge/docs/${detail.doc_id}?page=${point.page_no}`}
                    >
                      {format(t.revision.openPage, { page: point.page_no })}
                    </Link>
                  </Button>
                ) : null}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
