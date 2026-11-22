import { useEffect, useState } from "react";

import {
  PageEmpty,
  PageError,
  PageHeader,
  PageLoading,
} from "@/components/layout/page-states";
import { Card, CardContent } from "@/components/ui/card";
import { profileApi, type MasteryTopic } from "@/lib/api/profile";
import { useT } from "@/lib/i18n";

export function ProfilePage() {
  const t = useT();
  const [topics, setTopics] = useState<MasteryTopic[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  useEffect(() => {
    let cancelled = false;
    profileApi
      .mastery()
      .then((response) => {
        if (cancelled) return;
        setTopics(response.topics);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl space-y-4 p-6">
        <PageHeader title={t.profile.title} description={t.profile.subtitle} />
        {status === "loading" ? (
          <PageLoading />
        ) : status === "error" ? (
          <PageError title={t.common.errorTitle} description={t.common.errorBody} />
        ) : topics.length === 0 ? (
          <PageEmpty title={t.profile.emptyTitle} description={t.profile.emptyBody} />
        ) : (
          <Card>
            <CardContent className="space-y-5 pt-6">
              <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-gray-400" />
                  {t.profile.coveredLegend}
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-green-500" />
                  {t.profile.masteredLegend}
                </span>
              </div>
              {topics.map((topic) => {
                const coveredPercent =
                  topic.total > 0
                    ? Math.round((topic.covered_count / topic.total) * 100)
                    : 0;
                const masteredPercent =
                  topic.total > 0
                    ? Math.round((topic.mastered_count / topic.total) * 100)
                    : 0;
                return (
                  <div key={topic.topic} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{topic.topic}</span>
                      <span className="text-muted-foreground">
                        {topic.mastered_count}/{topic.total}
                      </span>
                    </div>
                    <div className="relative h-3 overflow-hidden rounded-full bg-muted">
                      <div
                        className="absolute inset-y-0 left-0 rounded-full bg-gray-400"
                        style={{ width: `${coveredPercent}%` }}
                      />
                      <div
                        className="absolute inset-y-0 left-0 rounded-full bg-green-500"
                        style={{ width: `${masteredPercent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
