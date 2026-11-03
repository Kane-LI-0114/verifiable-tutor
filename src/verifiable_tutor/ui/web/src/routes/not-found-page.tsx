import { FileQuestionIcon } from "lucide-react";
import { Link } from "react-router";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { useT } from "@/lib/i18n";

export function NotFoundPage() {
  const t = useT();

  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <FileQuestionIcon />
          </EmptyMedia>
          <EmptyTitle>
            <h1 className="text-base font-semibold">{t.common.notFoundTitle}</h1>
          </EmptyTitle>
          <EmptyDescription>{t.common.notFoundBody}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button asChild>
            <Link to="/chat">{t.common.goHome}</Link>
          </Button>
        </EmptyContent>
      </Empty>
    </div>
  );
}
