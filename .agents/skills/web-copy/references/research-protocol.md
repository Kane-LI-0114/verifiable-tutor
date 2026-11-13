# Research protocol: capturing real site copy

The gate in `SKILL.md` depends on this file. A capture is valid only when all three are true:

1. The text came from the live page at the URL, not from a search result, an AI summary, or
   memory.
2. The text is page copy a visitor sees — headline, subhead, body, CTA, FAQ — not just
   navigation, footer, cookie or privacy chrome.
3. You saved it verbatim, with URL, method, timestamp, and at least 600 characters of page
   copy (or three substantive quotes: headline + two body lines).

If a site cannot meet that bar after the full chain, it is a failed reference. Failures are
reported, not counted.

## The fallback chain

Try in this order. Stop at the first method that yields real page copy.

### 1. Built-in `web_fetch`

```
web_fetch(url)
```

This returns rendered Markdown with an HTTP status line. Treat it as a success only when:

- status is 200, and
- the body contains headline-like and body-like sentences, and
- there is no captcha / bot-wall marker: `Captcha`, `Just a moment`, `Access denied`,
  `403 Forbidden`, `429`, `enable JavaScript`, `unusual traffic`.

Truncation is fine: if the tool reports "Content truncated" but returned at least 600
characters of page copy, that is a valid capture — record that it was truncated.

Common failure modes and what to do:

- **Cross-origin redirect not followed** (for example `https://tutor.com` →
  `https://www.tutor.com`). Retry the exact URL named in the error. This is a retry, not a
  failure.
- **Only the title comes back** (JS-rendered SPA). Go to step 2.
- **Cookie/privacy modal dominates the text** (common on Chinese platforms). The actual page
  copy was never delivered — go to step 2.
- **403 / 429 / captcha.** Go to step 2.

### 2. `agent-browser` skill

Load the skill (`skill` tool, name `agent-browser`) and follow its instructions. The goal:

- open the URL in a real browser,
- wait for network idle plus ~1.5 s,
- dismiss a cookie/privacy banner if one blocks the page,
- read `document.body.innerText` (or the main landmark),
- save a screenshot next to the evidence file.

Use this for JS shells, bot walls that a browser passes, and pages whose text only appears
after hydration. Record the browser method and the extraction call in the evidence file.
If the browser cannot load the page (login wall, hard captcha), this site fails.

### 3. `curl` (server-rendered pages)

```bash
curl -L --max-time 25 -sS -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
  AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36" \
  "$URL" -o /tmp/page.html
```

Then strip `script`, `style`, and `noscript` and extract visible text with Python's
`html.parser`. This works for SSR marketing pages. For a React/Vue SPA it returns the shell
and must be treated as a failure.

### 4. Same-site alternates

Only if they contain the same visible copy:

- `/llms.txt` (some documentation sites publish a text version),
- a print view or AMP version of the same page,
- a static marketing page linked from the homepage (if the homepage itself was a shell).

A sitemap or `robots.txt` is not copy and does not count.

### Never counts

- `web_search` snippets or AI overviews,
- third-party descriptions, app-store listings, review sites,
- browser translation output (translate after capture, not instead of it),
- the model's memory of what the site says,
- a colleague agent's paraphrase.

## Evidence file

Save to `docs/copy-research/<YYYYMMDD>-<slug>.md`:

```markdown
# Copy research — <page or feature> — <date>

## References
| # | Site | URL | Captured at | Method | Page copy (chars) | Status |
|---|---|---|---|---|---|---|
| 1 | Khanmigo | https://www.khanmigo.ai/ | 2026-11-13 16:40 +08:00 | web_fetch | 6,200 | captured |
| 2 | Quizlet | https://www.quizlet.com/ | 2026-11-13 16:41 +08:00 | web_fetch → agent-browser | 0 | failed: captcha |
| 3 | Coursera | https://www.coursera.org/ | 2026-11-13 16:42 +08:00 | web_fetch | 42 (title only) | failed: JS shell |

## Quotes
### Khanmigo — https://www.khanmigo.ai/
- "Khanmigo is your always-available teaching assistant." (hero)
- "Build your brain power." (learner section)
- "guides learners to find the answer themselves" (FAQ)

### <site> — <url>
- ...

## Failures
- https://www.quizlet.com/: web_fetch 403, body "Captcha Challenge…"; agent-browser
  blocked by captcha. Replaced with <site>.
- https://www.coursera.org/: web_fetch 200 but only the document title; agent-browser not
  attempted because the page requires sign-in for copy. Replaced with <site>.
```

## Failure taxonomy

| Symptom | Meaning | Next |
|---|---|---|
| HTTP 301/302 to another host | Redirect not followed | Retry the canonical URL |
| HTTP 403 / 429 | Bot wall or rate limit | agent-browser, then give up |
| Body is "Captcha…" | Human check | agent-browser; if still blocked, fail |
| Body is only `<title>` | JS shell | agent-browser, then curl (SSR only) |
| Body is cookie/privacy modal + footer | Payload never delivered | agent-browser |
| Login required | Private page | Fail; do not use credentials |
| < 600 chars of visible copy | Insufficient | Count as failed |

## Rules of engagement

- Public pages only. Do not log in, do not bypass paywalls, do not solve captchas.
- At most five requests per domain per run; space retries by a second or two.
- Keep quotes short (a line or two per point). The evidence file is a record, not a copy of
  the site.
- Respect the site's terms; if a site forbids automated access, treat it as a failed
  reference and move on.
