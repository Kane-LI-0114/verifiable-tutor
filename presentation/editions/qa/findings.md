# Findings: stage HTML (resolved)

Updated 2026-11-25 after the builder re-exported the stage deck at 17:25. No open blockers
remain. The stage verdict in `qa-report.md` is PASS on the post-fix re-audit.

## Resolved blockers

All four blockers from the previous build were re-checked against the new artifacts.

### B-1: slide 5 blank bottom band (was 19.8 percent)

- Fixed: the cards are raised and the lowest content now ends at 936 of 1080 px, so the blank
  band is 13.3 percent, under the 15 percent cap.
- Evidence: `stage-html/exports/audit/font-audit.json` layout entry 5, `safeBottom=936`; the
  independent DOM audit reports 936; the pixel scan of the new `exports/png/slide-05.png` finds
  the last active row at 936.

### B-2: slide 19 blank bottom band (was 26.6 percent)

- Fixed: the A1 slide now has a 16:9 work-chain screenshot and an Evidence block filling the
  middle. The lowest content ends at 1001 of 1080 px, so the blank band is 7.3 percent.
- Evidence: `font-audit.json` layout entry 19, `safeBottom=1001`; independent DOM audit 1001;
  pixel scan of the new `exports/png/slide-19.png` finds the last active row at 1001.

### B-3: slide 19 label collision `LANGGRAPHTYPED`

- Fixed: the A1 labels are tracking-free 32 px cells. `LANGGRAPH` and `TYPED TOOLS` no longer
  overlap and the icon row reads cleanly.
- Evidence: the new `exports/png/slide-19.png` inspected at 1920x1080; the computed type audit
  still reports exactly [32, 96] on slide 19.

### B-4: slide 19 inverted shipped/planned legend

- Fixed: cobalt marks the shipped path (SPA, API, Gate, LangGraph, typed tools, model, store,
  SSE) and the Verifier is a dashed partial box. The legend now matches the v2 and custom
  editions and the rest of the deck.
- Evidence: the new `exports/png/slide-19.png`; the computed palette audit records cobalt
  1447E6 on slide 19.

## Remaining non-blocking polish

The slide 4 dangling separators, slide 5 and 6 label wraps, slide 15 clipped refusal crop, slide
9 clipped source-pane edge, palette deviations, and low-contrast gray 525252 are recorded as
polish in `qa-report.md`. Speaker notes are present and correct in the `SPEAKER_NOTES` runtime
object, and the `8 / 8` rendering is consistent with the frozen fact.
