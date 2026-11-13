---
name: web-copy
description: Write and rewrite user-facing copy for the Verifiable Tutor web app so it reads like a real education product instead of generic AI marketing. Use this skill whenever you add or change any visible text in src/verifiable_tutor/ui/web — headlines, taglines, nav labels, auth and onboarding screens, empty states, error messages, buttons, feature blurbs, practice/knowledge/deadlines/builds pages, or instructor console text — including when the user only asked for a layout, feature, or bug fix and did not mention copy. Also use when the user says the copy sounds like AI, generic, 文案 AI 味太重, 太像 AI 写的, or asks to make it sound like comparable sites. The skill requires capturing real copy from live comparable sites before writing; if capture fails, research failed and no copy is written from memory.
---

# Web copy that sounds like a real education product

This project is a course-grounded AI tutor. Its copy should read like a product built by
people who know the course — calm, specific, checkable — not like a landing page assembled
from SaaS adjectives. That difference comes from one thing: the wording is modeled on copy
that real products of this type actually ship, captured from their live pages, not from the
model's sense of what marketing sounds like.

## What this skill guarantees

- Every voice decision traces to a quoted line captured from a live, comparable site.
- Copy that the user did not explicitly ask for (a new page needs a headline, an empty state
  needs a sentence) is still copy. This skill applies to it.
- If the reference copy cannot be captured, the run reports failure and writes nothing.
  A failed fetch is not "close enough" and search snippets are not evidence.

## The gate (non-negotiable)

Before writing any copy on a Tier A job — or a Tier B job with no verified profile — capture
visible copy from **at least 3 distinct live sites of the same product type** (see
[references/research-protocol.md](references/research-protocol.md)). Each site needs a real
capture: the URL, the capture method, the time, and verbatim quotes saved to an evidence
file. If, after trying the full fallback chain, fewer than 3 sites are captured, stop.
Report what failed and why.

A Tier B job may reuse a profile in `docs/copy-research/profiles/` only if that profile
records at least 3 real captures with URLs and quotes (see
[references/voice-profile.md](references/voice-profile.md)).

A site that fails is not a success and is not used; replace it and record the failure. What
invalidates the run is claiming research succeeded without captured content — not the
existence of a failed attempt. Do not fall back to memory, search-result snippets, or "what
these sites usually say".

Why this is strict: the user's requirement is that no claim of research survives a failed
fetch. A model can always produce plausible marketing prose; the only thing that makes this
skill different is that the prose is anchored in text someone can check.

## Workflow

### Step 0 — Classify the job

- **Site type**: this project is an education / AI-tutor product (course Q&A, practice,
  knowledge base, instructor console). Reference sites must come from that genre, not from
  generic developer tools or consumer apps.
- **Copy tier**:
  - **A — full research**: new page, hero, tagline, onboarding, auth flow, feature
    descriptions, any copy where voice carries weight. Capture 3+ sites fresh.
  - **B — microcopy**: button labels, field errors, empty states, confirmations inside an
    established page. Reuse a verified profile from `docs/copy-research/profiles/` if one
    exists for this site type. The profile must record source URLs, capture date, and quotes.
    If no profile exists, run Tier A — one short pass is enough, but it must be real.

### Step 1 — Choose references

Pick 3–5 sites that share the product's job, with different angles:

- AI tutor / guided learning (e.g. Khanmigo, Brilliant)
- Human tutoring service (e.g. Tutor.com)
- Course platform / MOOC (e.g. Coursera, edX, icourse163)

Prefer at least one Chinese-language site when the deliverable includes `zh.ts`. Avoid
picking five clones of the same company — the point is to find the genre norm, not one
brand's voice.

### Step 2 — Capture

Follow [references/research-protocol.md](references/research-protocol.md). Short version:

1. `web_fetch` the page.
2. If it returns a JS shell, bot wall, captcha, or a cross-origin redirect, retry the
   canonical URL and then load the `agent-browser` skill to render the page and read
   `document.body.innerText`.
3. If the browser path is unavailable, try `curl` for server-rendered pages and strip tags.
4. Never count search snippets, AI summaries, third-party descriptions, or memory.

Record every attempt, including failures, in the evidence file. Navigation, footers, cookie
notices, and privacy modals are not page copy — a page that returns only those does not
count.

### Step 3 — Extract the voice profile

Use [references/voice-profile.md](references/voice-profile.md). For each dimension, write
the observation and the quote that supports it. Then synthesize: what do at least two of
the three sites do? That is the genre norm to imitate. Outliers are noted, not copied.

The profile is the deliverable of the research step. If it has no quotes, the research is
not done.

### Step 4 — Draft the copy

Write English first, in `src/verifiable_tutor/ui/web/src/lib/i18n/en.ts`, then write the
Chinese in `zh.ts` as native Chinese for the same intent — not a word-for-word translation.

- Keep the existing key structure. Add keys only when no existing key fits; `i18n.test.tsx`
  fails if `en` and `zh` do not have identical keys.
- Copy may only claim what the project actually does. Facts come from `docs/prd.md`,
  `GLOSSARY.md`, `README.md`, or the code. No invented numbers, testimonials, awards, or
  "thousands of students".
- Voice rules from the genre: address the reader directly, name the concrete role or task,
  prefer verbs over nominalizations, vary sentence length, let one sentence carry one idea.
- Avoid the structures in [references/banned-and-overused.md](references/banned-and-overused.md):
  triads, "not just X, but Y", em-dash chains, rhetorical-question openers, emoji bullets,
  and the usual hype vocabulary.

### Step 5 — De-AI pass

Read the draft as if it were a competitor's page. For each line ask: could this sentence
appear on any education product's site? If yes, replace it with something only this product
could say — the citation check, the deadline policy, the course's own material.

Then run the checklist in [references/banned-and-overused.md](references/banned-and-overused.md)
and the genre patterns in [references/education-copy-patterns.md](references/education-copy-patterns.md).

### Step 6 — Verify

- Evidence file complete: ≥3 sites, each with URL, method, timestamp, and quotes.
- No sentence copied verbatim from a reference site (pattern-level mimicry only). Check for
  runs of 8+ identical words; rewrite if found.
- Every factual claim maps to a project document or the code.
- From `src/verifiable_tutor/ui/web`: `npx vitest run tests/i18n.test.tsx` and
  `npm run typecheck`.
- If the gate failed, deliver the failure report only.

### Step 7 — Report

Use this shape:

```markdown
## Copy research
| Site | URL | Method | Captured at | Evidence |
|---|---|---|---|---|
| ... | ... | web_fetch / agent-browser / curl | ... | quotes + char count |

## Voice profile (condensed)
- ...

## Changes
| File | Key | Before | After | Why (evidence) |
|---|---|---|---|---|

## Verification
- i18n parity: pass/fail
- typecheck: pass/fail
- copied phrases: none

## Failures
- <url>: <what was tried> → <exact error / shell / bot wall>
```

When the gate fails, the report says so in the first line: `调研未成功` / `Research failed`,
then the attempts, then the options (fix access, provide captured text, or choose another
reference). No copy is written in that run.

## Evidence locations

- Full capture: `docs/copy-research/<YYYYMMDD>-<page-or-feature>.md`
- Reusable profile: `docs/copy-research/profiles/<site-type>.md`
- The profile records: source URLs, capture date, method, quotes, and the synthesis. A
  profile without those is not reusable.

## Project defaults

- Audience: CSIT6000V students, plus instructors/TAs for the console.
- Promise: answers grounded in the course's own material, with citations a reader can
  check; disclosure rules applied by policy; practice answers verified before grading.
- Tone: calm, precise, academic. No exclamation marks, no emoji, no salesmanship.
- Good existing examples: "Course-grounded answers with evidence you can check." and
  "以课程材料为依据、引用可核查的答疑。"
- Chinese should read like native product Chinese: short clauses, verbs first, no
  translationese ("开启您的学习之旅"), no idiom stacking.

## Pitfalls

- Treating whatever `web_fetch` returns as the page. Check that it contains headline and
  body copy, not just nav, footer, or a cookie dialog.
- Counting a site whose fetch returned only `<title>`.
- Calling the research done because three URLs were attempted. Captured ≠ attempted.
- Copying a competitor's sentence. Imitate the pattern, never the wording.
- Translating `en.ts` literally into `zh.ts`; the parity test checks keys, not quality.
- Inventing a metric or a quote to make the copy sound concrete.
- Editing generated artifacts (for example `proposal/` output) instead of the source.
