import { useState } from "react";

import { PageEmpty, PageError, PageHeader, PageLoading } from "@/components/layout/page-states";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CodeBlock, CodeBlockContent } from "@/components/ui/code-block";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Item, ItemContent, ItemTitle, ItemDescription, ItemActions } from "@/components/ui/item";
import {
  Trace,
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import { CheckCircle2Icon, CircleDashedIcon, Loader2Icon, XCircleIcon } from "lucide-react";
import { useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";
import { PREVIEW_BUILDS } from "@/lib/preview/fixtures";
import type { BuildState, KnowledgeBuild } from "@/lib/types";

const TIMELINE: BuildState[] = ["queued", "running", "ready"];

function stateIcon(state: BuildState) {
  if (state === "ready") {
    return <CheckCircle2Icon className="size-3.5 text-emerald-600" />;
  }
  if (state === "failed") {
    return <XCircleIcon className="size-3.5 text-destructive" />;
  }
  if (state === "running") {
    return <Loader2Icon className="size-3.5 animate-spin" />;
  }
  return <CircleDashedIcon className="size-3.5" />;
}

function timelineFor(build: KnowledgeBuild): BuildState[] {
  if (build.state === "failed") {
    return ["queued", "running", "failed"];
  }
  return TIMELINE;
}

export function BuildsPage() {
  const t = useT();
  const { pageState } = usePreview();
  const [selectedId, setSelectedId] = useState(PREVIEW_BUILDS[0]?.id ?? null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const selected = PREVIEW_BUILDS.find((build) => build.id === selectedId) ?? null;

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 p-6">
        <PageHeader
          title={t.builds.title}
          description={t.builds.subtitle}
          actions={
            <Button type="button" onClick={() => setDialogOpen(true)}>
              {t.builds.newBuild}
            </Button>
          }
        />

        <Alert>
          <AlertTitle>{t.builds.previewNotice}</AlertTitle>
          <AlertDescription>{t.builds.instructorOnly}</AlertDescription>
        </Alert>

        {pageState === "loading" ? (
          <PageLoading />
        ) : pageState === "error" ? (
          <PageError title={t.common.errorTitle} description={t.common.errorBody} />
        ) : pageState === "empty" ? (
          <PageEmpty title={t.builds.emptyTitle} description={t.builds.emptyBody} />
        ) : (
          <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
            <div className="space-y-2" aria-label={t.builds.title}>
              {PREVIEW_BUILDS.map((build) => (
                <Item
                  key={build.id}
                  variant={build.id === selectedId ? "muted" : "default"}
                  asChild
                >
                  <button
                    type="button"
                    className="w-full text-left"
                    onClick={() => setSelectedId(build.id)}
                  >
                    <ItemContent>
                      <ItemTitle>{build.id}</ItemTitle>
                      <ItemDescription>
                        {build.job_id
                          ? `${t.builds.jobId}: ${build.job_id}`
                          : t.builds.states[build.state]}
                        {build.records_count === null
                          ? ""
                          : ` · ${build.records_count}`}
                      </ItemDescription>
                    </ItemContent>
                    <ItemActions>
                      <Badge
                        variant={
                          build.state === "failed"
                            ? "destructive"
                            : build.state === "ready"
                              ? "secondary"
                              : "outline"
                        }
                      >
                        {t.builds.states[build.state]}
                      </Badge>
                    </ItemActions>
                  </button>
                </Item>
              ))}
            </div>

            {selected ? (
              <Card>
                <CardHeader>
                  <CardTitle>
                    <h2 className="text-sm font-semibold">{t.builds.details}</h2>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <dl className="grid grid-cols-2 gap-2 text-sm">
                    <dt className="text-muted-foreground">{t.builds.state}</dt>
                    <dd>
                      <Badge variant="outline">{t.builds.states[selected.state]}</Badge>
                    </dd>
                    <dt className="text-muted-foreground">{t.builds.jobId}</dt>
                    <dd className="font-mono text-xs">{selected.job_id ?? "—"}</dd>
                    <dt className="text-muted-foreground">{t.builds.records}</dt>
                    <dd>
                      {selected.records_count === null
                        ? "—"
                        : selected.records_count}
                    </dd>
                    <dt className="text-muted-foreground">{t.builds.createdAt}</dt>
                    <dd className="text-xs">{selected.created_at}</dd>
                    <dt className="text-muted-foreground">{t.builds.updatedAt}</dt>
                    <dd className="text-xs">{selected.updated_at}</dd>
                  </dl>

                  <section className="space-y-1">
                    <h3 className="text-sm font-medium">{t.builds.timeline}</h3>
                    <Trace>
                      {timelineFor(selected).map((state) => (
                        <TraceLine key={state}>
                          <TraceIcon>{stateIcon(state)}</TraceIcon>
                          <TraceTitle>{t.builds.states[state]}</TraceTitle>
                        </TraceLine>
                      ))}
                    </Trace>
                  </section>

                  <section className="space-y-1">
                    <h3 className="text-sm font-medium">{t.builds.request}</h3>
                    <CodeBlock size="sm">
                      <CodeBlockContent>
                        {JSON.stringify(selected.request, null, 2)}
                      </CodeBlockContent>
                    </CodeBlock>
                  </section>

                  {selected.error ? (
                    <Alert variant="destructive">
                      <AlertTitle>{t.builds.error}</AlertTitle>
                      <AlertDescription>{selected.error}</AlertDescription>
                    </Alert>
                  ) : null}
                </CardContent>
              </Card>
            ) : null}
          </div>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.builds.newBuild}</DialogTitle>
            <DialogDescription>{t.builds.subtitle}</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="build-doc">{t.builds.docId}</FieldLabel>
              <Input id="build-doc" placeholder={t.builds.docIdPlaceholder} />
            </Field>
            <Field>
              <FieldLabel htmlFor="build-chunks">{t.builds.maxChunks}</FieldLabel>
              <Input id="build-chunks" type="number" defaultValue={8} />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDialogOpen(false)}
            >
              {t.builds.cancel}
            </Button>
            <Button type="button" disabled title={t.common.unavailable}>
              {t.builds.start}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
