import { CalendarClockIcon, ShieldAlertIcon } from "lucide-react";

import { PageEmpty, PageError, PageHeader, PageLoading } from "@/components/layout/page-states";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useI18n, useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";
import { PREVIEW_DEADLINES } from "@/lib/preview/fixtures";

function formatDate(value: string, locale: string): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function DeadlinesPage() {
  const t = useT();
  const { lang } = useI18n();
  const locale = lang === "zh" ? "zh-CN" : "en-GB";
  const { pageState } = usePreview();
  const registry = PREVIEW_DEADLINES;
  const hasUnknown = registry.entries.some((entry) => entry.state === "unknown");

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-4 p-6">
        <PageHeader title={t.deadlines.title} description={t.deadlines.subtitle} />

        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="outline">
            {t.deadlines.version}: {registry.version}
          </Badge>
          <Badge variant="secondary">
            <CalendarClockIcon />
            {t.deadlines.clock}: {formatDate(registry.clock, locale)}
          </Badge>
          <span className="text-xs text-muted-foreground">{t.deadlines.readOnly}</span>
        </div>

        {hasUnknown ? (
          <Alert variant="destructive">
            <ShieldAlertIcon />
            <AlertTitle>{t.deadlines.failClosedTitle}</AlertTitle>
            <AlertDescription>{t.deadlines.failClosedBody}</AlertDescription>
          </Alert>
        ) : null}

        {pageState === "loading" ? (
          <PageLoading />
        ) : pageState === "error" ? (
          <PageError title={t.common.errorTitle} description={t.common.errorBody} />
        ) : pageState === "empty" ? (
          <PageEmpty
            title={t.deadlines.emptyTitle}
            description={t.deadlines.emptyBody}
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>
                <h2 className="text-sm font-semibold">{t.deadlines.assignment}</h2>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t.deadlines.assignment}</TableHead>
                    <TableHead>{t.deadlines.release}</TableHead>
                    <TableHead>{t.deadlines.due}</TableHead>
                    <TableHead>{t.deadlines.extension}</TableHead>
                    <TableHead>{t.deadlines.state}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {registry.entries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="font-medium">{entry.title}</TableCell>
                      <TableCell className="text-xs">
                        {formatDate(entry.release, locale)}
                      </TableCell>
                      <TableCell className="text-xs">{formatDate(entry.due, locale)}</TableCell>
                      <TableCell className="text-xs">
                        {entry.extension_until
                          ? formatDate(entry.extension_until, locale)
                          : "—"}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            entry.state === "unknown"
                              ? "destructive"
                              : entry.state === "active"
                                ? "secondary"
                                : "outline"
                          }
                        >
                          {t.deadlines.states[entry.state]}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        <p className="text-xs text-muted-foreground">{t.deadlines.previewNotice}</p>
      </div>
    </div>
  );
}
