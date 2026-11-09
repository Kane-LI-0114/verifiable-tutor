import { useT } from "@/lib/i18n";

/** Each dot starts a little later, so the three read as one travelling wave. */
const DOT_DELAYS_MS = [0, 150, 300];

/**
 * Holds the first line of where the answer will appear while the model has not
 * sent a token yet.
 *
 * The row keeps one line of the answer's own type (`text-sm leading-relaxed`),
 * so the answer's arrival replaces it without moving the thread. The dots carry
 * no text of their own: the label is the answer's status, and the thread's log
 * region announces it. Nothing here is a bubble, because an answer never is.
 */
export function AnswerPending() {
  const t = useT();

  return (
    <div
      data-slot="answer-pending"
      className="flex min-h-[1.625em] items-center gap-1.5 text-sm leading-relaxed"
    >
      <span className="sr-only">{t.chat.generating}</span>
      {DOT_DELAYS_MS.map((delay) => (
        <span
          key={delay}
          aria-hidden="true"
          className="size-1.5 shrink-0 rounded-full bg-muted-foreground animate-[answer-pending-dot_1.15s_ease-in-out_infinite] motion-reduce:animate-none"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}
