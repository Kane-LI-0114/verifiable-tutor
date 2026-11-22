import { format } from "@/lib/i18n";
import type { Messages } from "@/lib/i18n/en";
import type { CitationSource } from "@/lib/types";

const COURSE = "course";

type SourceCountKey =
  | "sourceCourseCount"
  | "sourceCourseCountOne"
  | "sourceWebCount"
  | "sourceWebCountOne";

function countLabel(
  t: Messages,
  count: number,
  many: SourceCountKey,
  one: SourceCountKey,
): string {
  return format(t.chat[count === 1 ? one : many], { count });
}

/**
 * The one-line tally both the source capsule and the inline disclosure show:
 * course pages first, then web pages, joined with a middle dot.
 */
export function sourceSummaryLabel(
  sources: CitationSource[],
  t: Messages,
): string {
  const course = sources.filter((source) => source.kind === COURSE).length;
  const web = sources.length - course;
  const parts: string[] = [];
  if (course > 0) {
    parts.push(
      countLabel(t, course, "sourceCourseCount", "sourceCourseCountOne"),
    );
  }
  if (web > 0) {
    parts.push(countLabel(t, web, "sourceWebCount", "sourceWebCountOne"));
  }
  return parts.join(" · ");
}
