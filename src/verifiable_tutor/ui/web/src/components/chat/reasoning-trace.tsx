import { BrainIcon } from "lucide-react";

import {
  Trace,
  TraceCollapsible,
  TraceCollapsibleContent,
  TraceCollapsibleTrigger,
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import { useT } from "@/lib/i18n";

export function ReasoningTrace({ reasoning }: { reasoning: string }) {
  const t = useT();

  return (
    <Trace>
      <TraceCollapsible>
        <TraceCollapsibleTrigger>
          <TraceLine>
            <TraceIcon>
              <BrainIcon />
            </TraceIcon>
            <TraceTitle>{t.chat.reasoning}</TraceTitle>
          </TraceLine>
        </TraceCollapsibleTrigger>
        <TraceCollapsibleContent>
          <p className="whitespace-pre-wrap text-sm">{reasoning}</p>
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>
  );
}
