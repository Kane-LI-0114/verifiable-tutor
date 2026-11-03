import { ShieldAlertIcon } from "lucide-react";
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

export function ForbiddenPage() {
  const t = useT();

  return (
    <div className="flex min-h-0 flex-1 items-center justify-center p-6">
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <ShieldAlertIcon />
          </EmptyMedia>
          <EmptyTitle>
            <h1 className="text-base font-semibold">{t.common.forbiddenTitle}</h1>
          </EmptyTitle>
          <EmptyDescription>{t.common.forbiddenBody}</EmptyDescription>
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
