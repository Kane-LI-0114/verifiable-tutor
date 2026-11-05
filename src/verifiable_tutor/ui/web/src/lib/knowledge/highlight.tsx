/**
 * Marker highlight for search hits.
 *
 * The backend returns the half-open ranges it matched, so the page marks
 * exactly those and never re-matches the query itself. That keeps the marking
 * and the match from disagreeing.
 */

export interface HighlightProps {
  text: string;
  ranges: [number, number][];
}

export function HighlightedText({ text, ranges }: HighlightProps) {
  if (ranges.length === 0) {
    return <>{text}</>;
  }
  const ordered = [...ranges]
    .filter(([start, end]) => start >= 0 && end <= text.length && end > start)
    .sort((left, right) => left[0] - right[0]);
  const parts: { value: string; marked: boolean }[] = [];
  let cursor = 0;
  for (const [start, end] of ordered) {
    if (start < cursor) {
      continue;
    }
    if (start > cursor) {
      parts.push({ value: text.slice(cursor, start), marked: false });
    }
    parts.push({ value: text.slice(start, end), marked: true });
    cursor = end;
  }
  if (cursor < text.length) {
    parts.push({ value: text.slice(cursor), marked: false });
  }
  return (
    <>
      {parts.map((part, index) =>
        part.marked ? (
          <mark
            key={index}
            className="rounded-sm bg-yellow-200/70 px-0.5 text-foreground"
          >
            {part.value}
          </mark>
        ) : (
          <span key={index}>{part.value}</span>
        ),
      )}
    </>
  );
}
