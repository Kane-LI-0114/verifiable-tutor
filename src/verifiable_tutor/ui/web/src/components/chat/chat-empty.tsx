import { MessageSquareIcon } from "lucide-react";

import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";

export function ChatEmpty({ onPick }: { onPick: (suggestion: string) => void }) {
  const t = useT();

  return (
    <div className="flex flex-1 items-center justify-center overflow-y-auto p-6">
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <MessageSquareIcon />
          </EmptyMedia>
          <EmptyTitle>
            <h1 className="text-base font-semibold">{t.chat.emptyTitle}</h1>
          </EmptyTitle>
          <EmptyDescription>{t.chat.emptyBody}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <p className="text-xs font-medium text-muted-foreground">
            {t.chat.suggestionsTitle}
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {t.chat.suggestions.map((suggestion) => (
              <Button
                key={suggestion}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onPick(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </EmptyContent>
      </Empty>
    </div>
  );
}
