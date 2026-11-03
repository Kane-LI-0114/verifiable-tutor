import { cjk } from "@streamdown/cjk";
import { code } from "@streamdown/code";
import { createMathPlugin } from "@streamdown/math";
import { Streamdown } from "streamdown";

import { cn } from "@/lib/utils";

const math = createMathPlugin({ singleDollarTextMath: true });

export function Markdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <Streamdown
      className={cn("text-sm leading-relaxed", className)}
      plugins={{ code, math, cjk }}
    >
      {children}
    </Streamdown>
  );
}
