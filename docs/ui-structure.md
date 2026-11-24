# Browser UI structure

| | |
|---|---|
| **Status** | Milestone 3, authentication and chat wired to the local API; numbered turn sources, the answer source capsule, the per-answer citation source pane, and the knowledge-base browser are wired |
| **Date** | 2026-11-11 |
| **Scope** | Routes, layout regions, the components each page uses, states, and the boundary between live data and the offline preview demo |
| **Owner** | This file owns the page structure. [ADR-0003](adr/0003-react-spa-with-ai-elements.md) owns the frontend stack, [prd.md](prd.md) owns the behavior, and [tech-selection.md](tech-selection.md#ui-and-streaming-protocol) owns the build and serving decisions |

The UI source lives under `src/verifiable_tutor/ui/web/`. The build writes to `src/verifiable_tutor/ui/static/`, which Git ignores; the backend serves that directory on the same origin as the API ([factory.py](../src/verifiable_tutor/api/factory.py)). Milestone 2 wires the authentication flows, the server-side session, conversation history, streamed chat, and replay to the local API. Verified citations and page highlights, the deadline registry, voice input, and audio attachments still use preview structures; numbered sources, the answer source capsule, and the per-answer citation source pane are wired; practice generation, saved sessions, attempts, autosave, and grading are wired to the live API; TTS playback of assistant answers reads `POST /api/voice/speech/stream` as SSE PCM16 frames, while the whole-audio route `POST /api/voice/speech` stays available. The verified citation layer and the populated OCR image mirror arrive in a later milestone.

## Page map

| Route | Access | Purpose | Data source |
|---|---|---|---|
| `/login` | Public | Sign in with email and password | Live API, preview in demo mode |
| `/register` | Public | Register with a student email and password | Live API, preview in demo mode |
| `/verify?email=` | Public | Confirm the six digit code | Live API, preview in demo mode |
| `/reset` | Public | Request a password reset link | Live API, preview in demo mode |
| `/reset/confirm?token=` | Public | Set a new password from the link | Live API, preview in demo mode |
| `/chat` | Signed in | Start a new conversation | Live empty thread |
| `/chat/:sessionId` | Signed in | Conversation, work chain, answer source capsule, per-answer citation source pane; `?replay=1` replays the recorded trace | Live history and stream; replay trace |
| `/practice` | Signed in | Practice generator: pick a topic and question types to create a saved session | Live API |
| `/practice/:sessionId` | Signed in | Saved practice session: question form, attempt pages with a pager, autosave, stored grading, delete | Live API |
| `/knowledge` | Signed in | Browse the course archive as a folder and file grid, with a right-hand file pane | Live API |
| `/knowledge/docs/:docId?page=` | Signed in | Read one PDF page by page, with a chat pane on the right | Live API and a PDF fetch |
| `/instructor/builds` | Instructor | Start and watch a Qwen knowledge-base build | Preview fixture |
| `/instructor/deadlines` | Instructor | Read the deadline registry state | Preview fixture; the backend has no registry endpoint yet |
| `*` | Public | Not found | None |

Authentication routes render in a centered column without the application shell. Every other route renders inside the shell. The instructor routes are nested under the same navigation group as the student routes, but their menu entries are hidden for a student and the route guard renders the forbidden page for a student.

## Layout regions

```text
┌───────────────────────────────────────────────────────────────┐
│ Top bar: sidebar toggle, page title, language, preview        │
├───────────────┬───────────────────────────────┬───────────────┤
│ Sidebar       │ Thread                        │ Sources       │
│ Logo          │ Work chain                    │ Resize handle │
│ New question  │ Reasoning                     │ Source rows   │
│ Practice      │ Markdown and [ref_n] markers  │ Thumbnail     │
│ Knowledge     │ Source capsule, tool calls    │ Title/summary │
│ Instructor    │ Composer                      │ Type/page     │
│ Conversations │                               │ Close button  │
│ Account menu  │                               │               │
└───────────────┴───────────────────────────────┴───────────────┘
```

The sidebar has no separate Chat entry: New question opens an empty conversation and the conversation list opens an existing one. Conversations and practice sessions are grouped separately. The practice group carries a status label per row (Not started, In progress, or best score over the maximum) and a two-way filter (All, Not started); a practice row opens `/practice/:sessionId`, while a legacy practice conversation without a stored session opens in the chat view. The sidebar collapses to a 48px icon rail; in that state only the logo, the nav icons, and the account avatar remain, and the account name is reachable through the avatar menu. The account menu and sign out live in the sidebar footer, not in the top bar.

On a narrow viewport the sidebar becomes a sheet that closes when a destination is chosen, and the citation source pane opens as a sheet from the answer source capsule. The other pages use one centered column with a page header.

The authentication pages use two columns on a wide viewport: product framing on the left and the form card on the right. A narrow viewport shows only the form card. The authentication pages and the not-found page render without the shell but keep the language switch and the preview controls in the top right corner, so a reviewer can always change role or language.

## Page composition

### Chat

| Region | Components | Notes |
|---|---|---|
| Thread | Message Scroller, Message, Bubble, Markdown | The user turn is a bubble; the assistant turn is a flat column |
| Work chain | Trace, Task, Badge | The expanded chain shows one section per step id that actually exists, ordered understand, retrieve, verify, decide, generate, cite, then by row position for same-phase rows. Each section shows the step status, duration, detail, policy, and rule id, followed by its events in order. A step with no events still shows its section. Steps that appear in neither `message_steps` nor an event step id are not synthesized. The header keeps the summary and policy badge, not a separate step rail |
| Thinking | Reasoning block inside its step section | Each model call's reasoning is a work-chain event tagged `generate` and renders under the generate section; there is no separate thinking section |
| Answer | Markdown with the math, code, and citation-marker plugins | Formulas through KaTeX, code through Shiki. `[ref_n]` becomes a source link that displays only `n` when the turn has sources; a bare `[1]` and an unknown token stay plain text |
| Source capsule | Source capsule on Button and AvatarGroup | Sits at the end of the answer, above the actions. Stacks up to three source thumbnails, shows `+N`, and summarizes the counts as course pages and web pages. It has no expand icon and is the only entry to the source pane |
| Citation source pane | Source pane, Source list, Source row, Source thumbnail | Opens for the answer whose capsule was clicked and slides between zero and its stored width. Lists that answer's retrieved sources in marker order, with each row fading in from the top; the top-right X closes it. A course row opens `/knowledge/docs/<doc>?page=N`, a web row opens the source URL in a new tab |
| Tool calls | Tool, Terminal, Code Block | Inside their step section, in event order, not at the end of the answer bubble: tool name, arguments, result summary, duration, optional command line and exit code, truncated output |
| Actions | Button, Tooltip | Copy, retry, speak. The speak action streams PCM16 frames from `POST /api/voice/speech/stream` into a Web Audio queue, becomes Stop while playing, and offers Retry after a failure |
| Composer | Input Group, Model Selector, Attachment | Provider and tier, thinking level, audio attachment (MiMo only), microphone control, send and stop. Enter sends, Shift+Enter inserts a newline, and Enter during an IME composition confirms the candidate instead of sending. The model and thinking choice persists in browser local storage (`vt.composer.selection`), so a refresh or another conversation keeps the last choice; missing or invalid stored data falls back to DeepSeek Flash with thinking off |

The model selector offers DeepSeek Flash, MiMo Flash, and MiMo Pro. DeepSeek exposes the four thinking levels; MiMo exposes only Off and On, the request carries `on`, and the adapter maps it to MiMo's `{"type": "enabled"}`. Switching to MiMo clamps a stored `low`, `high`, or `max` selection to On. All three values are sent with the live turn. In live mode the audio attachment and microphone controls stay disabled until the remaining voice wiring lands; TTS playback of assistant answers is wired to the streaming route. The preview demo keeps the attachment state and the DeepSeek capability error.

Changing the route from `/chat` to `/chat/:sessionId`, or to another session, remounts the conversation state and loads that conversation's history from `GET /api/sessions/{id}/messages`; `/chat` always starts empty. The conversation a finished first answer opens loads the same way, because the backend persists each answer's turn metadata with the answer; the work chain, thinking, numbered sources, and tool calls therefore survive the remount and every later reload. When the conversation is non-empty, a visually hidden `h1` names the conversation. Each live conversation also remembers its thread scroll position in browser local storage (`vt.chat.scroll.<sessionId>`), so reopening it or switching back restores the reading position; a conversation opened for the first time, replay, and the preview demo keep the default end position. The page keeps the last twenty loaded histories in memory for the signed-in user and warms them from the conversation list, so switching to a listed conversation renders from that cache while it revalidates, without flashing the loading state; the cache is dropped on sign-out, and sending a turn in a conversation drops its entry so the next visit reloads the stored history. The preview demo carries one seeded conversation per fixture session instead.

In live mode the chat state comes from `@ai-sdk/react` `useChat` with the project transport (`src/verifiable_tutor/ui/web/src/lib/chat/tutor-transport.ts`). The transport sends only the newest user text plus `session_id`, `provider`, `tier`, and `thinking` to `POST /api/chat`, because the backend owns the conversation history. The conversation id arrives in the `x-conversation-id` response header; a new conversation navigates to `/chat/<id>` after the stream finishes and the answer with its turn metadata is persisted. When a turn fails before the stream starts, the client keeps the conversation id from the same header, so a retry sends the question into that conversation instead of creating a second one. The streamed answer carries the request-time provider and tier as message metadata, so its badge does not follow a later composer change. A live work chain derives its step rail from the `data-step` custom data parts; reasoning text from `reasoning-*` frames and live tool calls from `data-tool` parts are composed into ordered work-chain events, which are the only content of the expanded chain; `data-sources` parts carry the turn's numbered sources. A stored turn renders the persisted step rail, ordered events, numbered sources, and tool calls that the history response returns, through the same components. A stream failure stops the answer, drops the partial text, shows the failure copy, and offers to put the question back in the composer; it is never replayed as if complete (FR-B12). Replay re-emits the recorded trace through the same components at a selectable speed, and the composer is hidden while replays run.

### Citation source pane

The pane lists one answer's retrieved sources in marker order. Each row carries the marker, a thumbnail, the title, a two-line summary, and a type line: the page number for a course source, the hostname for a web page. Course thumbnails come from `/api/corpus/<doc_id>/pages/<page_no>.webp`; web thumbnails come from the source site's `/favicon.ico`. Both fall back to a file or globe icon when the image is missing, and the preview build makes no external image request. The pane never claims that a source is verified: a marker names a retrieved source, not a citation that passed the span verifier.

A course row and a course marker navigate in the app to `/knowledge/docs/<doc_id>?page=<page_no>`, the paginated knowledge browser view. A web row and a web marker open the source URL in a new tab with `noopener noreferrer`. Hovering a marker shows the same `SourceItem` row the pane shows, using `HoverCard`. An unknown marker stays plain text.

On a wide viewport the pane opens only for the answer whose capsule was clicked and starts closed on every page load. It is mounted at width zero, so the first open and every close animate the width over 300ms; after opening, the rows fade in from the top with a 30ms stagger. The top-right control is an X, not the old collapse glyph. The default width is 380px, the minimum is 280px, and the maximum is `min(640px, 55% of the viewport)`. The drag handle on the pane's left edge uses `cursor: col-resize` and pointer capture; the same handle is a focusable separator with `aria-valuenow`, `aria-valuemin`, and `aria-valuemax`, arrow-key resizing in 16px steps, and Home/End for the bounds. A double click resets the width to 380px, and the width persists in local storage (`vt.sources.width`). The pane has no collapsed rail: the answer capsule is the only entry, and the pane's top-right X is the exit. The width animation and row fade are disabled under `prefers-reduced-motion`. Below 1024px the same list opens in a sheet from the capsule.

### Practice and self-test

The generator route holds the topic and type controls. Generating sends `POST /api/practice/sessions`, which generates the questions with the agent loop and saves the session before the first answer. The page stays on the generator, refreshes the sidebar practice list, and shows a ready notice with a button that opens the saved session. The five question types are single choice, multiple choice, true or false, short answer, and code. Choice answers use Radio Group or Checkbox, short answers and code use a Textarea.

The session route shows one page per attempt. The pager moves between attempts and the last page carries "Practice again", which opens the next attempt without changing the session status. Only an in-progress attempt is editable; earlier attempts are read-only and show their stored score and explanations. Objective questions render the choice order stored with the attempt, so the correct option is not always first and every new attempt reshuffles. Choice answers are graded deterministically in the browser, open and code answers go through `POST /api/practice/runs`, and the submission is stored with `POST /api/practice/sessions/{id}/attempts/{n}/submit`. Choosing an option autosaves immediately, typed answers autosave after a short debounce and on blur, and a reload resumes the same answers. The first attempt decides whether the session is not started, in progress, or completed; later attempts only raise the best score. Deleting removes only the current attempt and renumbers the rest; the practice disappears when its last attempt is deleted. The "My solution" tab and the TACC code-run job are not part of this page yet.

### Knowledge base

The page is a file browser over the local corpus ([ADR-0015](adr/0015-local-knowledge-store-and-chunking.md)). It has three regions inside the shell's main column, the same flex row the chat page uses: a header band, a tile grid, and a right-hand file pane.

The header band holds the breadcrumb, the search field, and a round `+` button. The breadcrumb starts at the root and lists every ancestor folder; each segment is a button that navigates to that folder. The `+` menu has two items: "Upload file", which is disabled with a title explaining that the TACC upload chain is not verified yet, and "New folder", which opens a naming dialog. The whole grid is a drop target that shows an overlay when files are dragged over it and refuses the drop with the same explanation; no request is made.

The grid shows folders first and files after them. The tiles keep a fixed size: every column track is 9rem wide and as many columns as fit wrap onto each row, so expanding or collapsing a sidebar changes how many columns fit, never the size of a tile. A row always reaches both edges of the pane: the width left over after the last column is shared out between the column gaps, so a narrower pane tightens the gutters instead of leaving dead space on the right. Each tile is a locked 4:3 landscape card whose face fills the whole tile: a file card is the rendered first page of the PDF, and a folder card is a muted face with a folder glyph and a chip naming how many files it holds. The file name (two lines maximum) sits on a scrim at the bottom of the face, and the status chip sits at the top left. Selecting a tile fills the right pane without leaving the page; double-clicking a file opens the document route. Both tile kinds carry an ellipsis button at the top right of the face with a 24px hit area: a folder offers "Move folder" and "Delete folder" (deleting the documents inside it), and a file offers "Move file" and "Delete file". The ellipsis is a separate button, so it never selects or opens the tile, and it is reachable by Tab. Delete actions use a confirmation dialog; the folder dialog names how many files it contains. Move actions use a folder-tree dialog that refuses to move a folder into itself or a descendant.

The file status is shown on the tile and in the right pane. On the tile, `uploading` dims the page preview and `uploaded` and `processing` pulse it, and each state carries a chip at the top left of the face with a spinner. `upload_failed` and `failed` show a failure badge whose title carries the reason, and `ready` shows nothing.

Searching replaces the grid with a flat result list grouped by document. Each result names why it matched (file name, folder, page text, or summary), shows the page number for a text hit, and marks the matched words in the snippet. The highlight ranges come from the API, not from a second client-side match, so the marking and the match cannot disagree.

The right pane is the same width, position, and drag behavior as the chat page's citation source pane. It shows the file name, the date it was added, the Qwen summary and the model that wrote it, the page and chunk counts, the localized document status, and a collapsed knowledge-card section fed by `GET /api/knowledge/cards?doc_id=`. With no selection it explains what selecting a file does. Below 1024px the pane is a sheet that opens on selection.

### Document preview

The document route replaces the whole knowledge-base region, not a dialog. The left side is the PDF reader; the header carries a back arrow that returns to the folder the reader came from, the file name, a two-state browse switch, the page indicator, previous and next buttons, and a page input. The switch offers page view and scroll view, defaults to page view, and remembers the choice in browser local storage (`vt.knowledge.preview.mode`).

Page view renders one page at a time: PageUp and PageDown move one page, and previous, next, or a page jump renders that page on the same canvas. Scroll view stacks every page in one scrolling column, renders only the pages near the viewport, scrolls to the page in the URL when the reader switches modes or jumps, and reports the page being read back to the URL, the page indicator, and the document chat context. The page input starts empty and clears after a jump, so it never shows a stale page number.

The right pane on this route is a conversation, not the file record: it has the message list, the same composer as the chat page (provider, tier, and thinking level persist through `vt.composer.selection`), and it sends `document_context` with `doc_id` and the current page so the answer knows what is open. The page body is not injected: the model calls `read_course_page` with that id and page when the question needs the text, so the turn carries the coordinates and the tool result carries the text. Below 1024px a button in the header opens the same conversation as a sheet.

Citations close each answer in place instead of opening a pane: the fold starts collapsed as the same thumbnail stack and count as the chat page's source capsule, and expanding it lists the course pages and web pages without leaving the thread. A History button at the top of the pane reloads the conversation already stored for this file, so a later visit continues the thread and its citations. The conversation is created on the first send and its id is remembered per document in browser local storage.

While a document is open, the knowledge item in the main navigation points at that file and page: leaving for the conversation view and returning resumes the document instead of the grid, and a click while already inside the knowledge section returns to the grid. The memory is in-memory only and is never stored, so a new tab starts at the grid.

### Knowledge-base builds

Instructors get a build list and a new-build dialog with the document id and the chunk limit. A build row shows the state, job id, record count, and timestamps. The detail view shows the state timeline, the request JSON, and the failure message with a retry action. The preview page uses the four states the backend defines: `queued`, `running`, `ready`, and `failed`. The PRD also asks for a `downloading` state; the backend does not emit it yet and the UI does not invent it.

### Deadline registry

Instructors get a read-only table of assignments with release date, due date, extension window, and the five policy states (`pre-release`, `active`, `extension-window`, `post-deadline`, `unknown`), plus the registry version and the injected clock. An unknown state shows the fail-closed notice. The in-app editor is P1 and the page says so. The backend has no registry endpoint yet.

## Theme and colour budget

The palette is one neutral family, one accent family, and one semantic family, defined as CSS custom properties in `src/verifiable_tutor/ui/web/src/styles/index.css`. Every value is an official Tailwind v4 OKLCH step, so no colour is hand-picked and none drifts as the ramp darkens.

| Family | Token | Value | Job |
|---|---|---|---|
| Neutral | `--background` | `oklch(1 0 0)` | page and card surface |
| Neutral | `--foreground` | `oklch(0.141 0.005 285.823)` | body text, zinc-950, 19.8:1 |
| Neutral | `--muted-foreground` | `oklch(0.439 0 0)` | secondary text, neutral-600, 7.8:1 |
| Neutral | `--border` | `oklch(0.922 0 0)` | rules and card edges, neutral-200 |
| Accent | `--primary`, `--ring` | `oklch(0.488 0.243 264.376)` | primary actions, links, focus, blue-700, 6.8:1 |
| Accent | `--sidebar-accent` | `oklch(0.488 0.243 264.376 / 0.12)` | current destination and hover |
| Semantic | `--destructive` | `oklch(0.505 0.213 27.518)` | failure text and destructive fill, red-700 |

Three rules keep the set closed:

- Cobalt marks interaction and provenance only: primary actions, links, focus rings, the current destination, and the markers that tie a claim to its page. Nothing else takes the hue.
- Red is failure and destructive action only, never decoration, and one red per view. There is no green or amber status colour; success is a cobalt tint with a check icon, a warning is ink with an icon.
- A border, hover wash, or disabled fill is a tint of one of the three families, not a further colour. `--radius` is `0.375rem`, cards keep a 1px rule and cast nothing, and only overlays cast a shadow.

Typography follows the same split. Page titles and the wordmark take Source Serif 4 with a Songti fallback, so both scripts get a serif at display sizes and a sans in the body; the Latin subset ships in `src/verifiable_tutor/ui/web/public/fonts/` under the OFL. `--input` sits at 3:1 because a field boundary is the only thing that identifies the control (WCAG 1.4.11), while `--border` stays light because a rule is decoration.

Motion follows one default: `--default-transition-duration` is 150ms and `--default-transition-timing-function` is `cubic-bezier(0.23, 1, 0.32, 1)`, so any transition that does not ask for its own duration leaves fast and settles. Panes ask for 300ms because a width change covers more ground, and the knowledge grid animates through `@formkit/auto-animate`. Every animation is skipped under `prefers-reduced-motion`.

`tests/theme-budget.test.ts` scans the component tree for a Tailwind colour utility outside the three families and fails the suite, because a stray hue is how a second identity leaks in. The `.dark` block still holds the original neutral values and is not wired to any control.

## Documented components and their sources

The stack decision is [ADR-0003](adr/0003-react-spa-with-ai-elements.md). The AI Elements patterns now live in shadcn/ui, and the older elements.ai-sdk.dev site is being retired. The UI installs the shadcn primitives and copies the pattern compositions into `src/verifiable_tutor/ui/web/src/components/ai/`.

```bash
npx shadcn@latest add sidebar button dropdown-menu avatar badge separator tooltip sheet \
  scroll-area skeleton breadcrumb field label input textarea input-otp input-group select \
  radio-group checkbox alert card collapsible tabs pagination empty table dialog progress \
  item spinner message-scroller message bubble attachment hover-card trace code-block
```

| ADR-0003 component | File | Source |
|---|---|---|
| Message scroller | `components/ui/message-scroller.tsx` | shadcn registry |
| Message bubbles | `components/ui/message.tsx`, `components/ui/bubble.tsx`, `components/chat/chat-message.tsx` | shadcn registry plus a composition |
| Pending answer | `components/chat/answer-pending.tsx` | composition on the message content |
| Trace and task timeline | `components/ui/trace.tsx`, `components/chat/work-chain.tsx` | shadcn registry plus a composition |
| Inline source marker | `components/ai/citation-markers.tsx` | streamdown remark plugin plus hover card and the project source row |
| Source capsule | `components/chat/source-capsule.tsx` | button and avatar group |
| Source pane and rows | `components/chat/source-pane.tsx`, `components/chat/source-list.tsx`, `components/chat/source-thumbnail.tsx` | side pane, item, badge, and empty primitives |
| Practice citation row and page panel | `components/practice/citation-row.tsx`, `components/practice/evidence-panel.tsx` | the page-image surface kept for the practice preview; chat no longer uses it |
| Code block | `components/ui/code-block.tsx` | shadcn registry |
| Prompt input | `components/ui/input-group.tsx`, `components/ui/attachment.tsx`, `components/chat/composer.tsx` | shadcn registry plus a composition |
| Model selector | inside `components/chat/composer.tsx` | composition on dropdown menu and input group |
| Tool and terminal | `components/chat/tool-call.tsx` | composition on trace and code block |
| Reasoning | `components/chat/reasoning-trace.tsx` | composition on trace |
| Confirmation | the dialog in `routes/practice/practice-page.tsx` | composition on dialog and button |
| Test results | `components/practice/test-results.tsx` | composition on trace and code block |
| Markdown with math and code | `components/ai/markdown.tsx` | streamdown with the code, math, and CJK plugins, KaTeX CSS |

The document pane uses a full-width citation fold in the answer's last line instead of the capsule, because it has no source pane to open. The live and preview chat pages render the shared session shell in `src/verifiable_tutor/ui/web/src/components/chat/chat-session-shell.tsx` (thread, pending answer placeholder, answer source capsule, sliding citation source pane, narrow-screen source sheet, and replay banner) and each page keeps its own data access; together they wire Message Scroller, the message composition, and the composer. They do not copy the documentation demos, which depend on a fake transport, `motion`, and Next.js helpers. Not every pattern needs its own file: model selection and confirmation are small compositions inside the page that uses them.

The pending answer placeholder holds the answer's first line open between sending a question and the first streamed frame, and again while a started answer has no text yet. The conversation shell and the document chat pane both render it, and its dot wave is the `answer-pending-dot` keyframes in `src/verifiable_tutor/ui/web/src/styles/index.css`. The shell treats the placeholder as the scrolling anchor, so the thread follows the answer from the moment it is awaited, and a reader gesture still hands the scroll back.

Not used yet: Plan, Context, Chain of Thought, Questionnaire, speech input patterns (built from a button and a native element), and animation. In live mode the streaming state comes from `@ai-sdk/react` `useChat` with the project transport; the preview demo keeps its fixture-based chat. Voice input and the audio attachment path stay structured but unwired; TTS playback of assistant answers is wired through `POST /api/voice/speech/stream` with Web Audio, while the whole-audio route stays available.

## States and preview mode

Live data is the default. The shell boots from `GET /api/auth/me`: a loading state while the session is read, the login redirect (`/login?next=`) for an anonymous visitor, and a retry state when the backend cannot be reached. An authenticated visitor who opens an authentication page is redirected into the app, using the preserved `next` path when it is a safe same-origin path. Signing out calls `POST /api/auth/logout`; a 401 from a later request (the conversation list, history, the chat stream, or replay) clears the client session and returns to the login page. Every page still renders loading, empty, error, and forbidden states.

The offline preview demo is an explicit opt-in: `VITE_PREVIEW=1` at build time, or `?preview=1` on a live build. On a live build the documented preview values also opt in: `?preview=loading`, `?preview=empty`, and `?preview=error` enter the demo and select that page state, while `?preview=1` enters it in the normal state; the `VITE_PREVIEW=1` build accepts the same state parameters. In preview mode the developer controls switch between signed out, student, and instructor, `?previewRole=instructor` selects a role on first load, and the choice persists in local storage. The authentication layout and the not-found page keep the language switch and the preview controls in their top right corner, so a signed-out reviewer can return to a role without clearing storage. The preview build makes no API request; the registration page validates against a demo domain fixture instead of the configured-domain endpoint.

## Data contracts and coverage

The TypeScript types in `src/verifiable_tutor/ui/web/src/lib/types.ts` mirror the JSON the backend returns. They do not add fields the backend does not have.

| Surface | Endpoint | Backend state | UI wiring |
|---|---|---|---|
| Registration, verification, login, logout, reset | `/api/auth/*` | Implemented | Wired in milestone 2 |
| Allowed registration domains | `GET /api/auth/domains` | Implemented, public, from `config/app.yaml` | Wired: the registration page checks the configured list (FR-A3), and a failed load defers to the backend |
| Current account and session bootstrap | `/api/auth/me` | Implemented | Wired in milestone 2 |
| Conversations and history | `/api/sessions`, `/api/sessions/{id}/messages` | Implemented: messages include persisted turn metadata (work steps, thinking, model profile, numbered sources, and tool calls; the verified `citations` list stays empty until the verifier lands) | Wired in milestone 2 |
| Chat stream | `POST /api/chat` | Implemented: `start-step` and `finish-step` per model call, `data-step` for generate and retrieve, `data-tool` for live tool activity, `data-sources` for the turn's numbered sources, `x-conversation-id`, thinking level, the resolved model selection in the trace meta, and the persisted turn before the `finish` frame | Wired in milestone 2 |
| Tool calls | `data-tool` frames and `tool_calls` rows | Implemented: name, provider call id, arguments, structured result, output, duration, status | Wired: live frames and history |
| Replay | `GET /api/sessions/{id}/replay` | Implemented, recorded trace frames | Wired in milestone 2 |
| Numbered sources | `data-sources` frames and `message_sources` rows, returned by the history API | Implemented | Wired: answer capsule, marker hover, and per-answer source pane |
| Verified citations and highlights | `citations` rows with quoted spans and page block coordinates | Producer missing; tracked by issue #1 | Structure only |
| Practice sessions and attempts | `POST /api/practice/sessions`, `GET /api/practice/sessions/{id}`, `PATCH .../attempts/{n}/answers`, `POST .../attempts/{n}/submit`, `POST .../attempts`, `DELETE /api/practice/sessions/{id}` | Implemented: questions persist at generation, the first attempt sets the status, later attempts only raise the best score | Wired: generator, attempt pager, autosave, delete |
| Practice grading | `POST /api/practice/runs` | Implemented: online model grading for open and code answers; choice answers are graded in the browser | Wired |
| Practice code execution | `tacc/exec` | Not implemented | None |
| Knowledge cards | `GET /api/knowledge/cards` | Implemented | Wired: the file pane's collapsed card section |
| Knowledge folders and files | `GET/POST/PATCH/DELETE /api/knowledge/folders`, `GET/PATCH/DELETE /api/knowledge/documents` | Implemented | Wired in milestone 3 |
| Document PDF | `GET /api/knowledge/documents/{doc_id}/file` | Implemented | Wired: the preview fetches it once |
| Knowledge search | `GET /api/knowledge/search` | Implemented | Wired: search field and result list |
| Retrieval preview | `GET /api/knowledge/retrieve` | Implemented; the agent `search_course` tool calls the same hybrid retriever | Not used by a page; the agent loop uses the retriever directly |
| Knowledge builds | `GET` and `POST /api/knowledge/builds` | Implemented, no downloading state | Fixture with four states |
| Deadline registry | None | Missing | Read-only fixture |
| Voice | `/api/voice/*` | Implemented | Wired: TTS playback of assistant answers through `POST /api/voice/speech/stream` SSE frames and Web Audio; `POST /api/voice/speech` still returns whole audio; ASR and the audio attachment path stay structured |
| Page image | `/api/corpus/{doc_id}/pages/{page_no}.webp` | Implemented, corpus mirror empty | Source thumbnail with icon fallback; knowledge page preview |

## TDD seams

The UI follows the red, green, refactor loop at these seams. The tests live in `src/verifiable_tutor/ui/web/tests/`.

| Seam | Test | Catches | Misses |
|---|---|---|---|
| Routes and guards | `router.test.tsx`, `live-session.test.tsx` | Default route, unauthenticated redirect, unavailable retry, role leak, unknown path | Server-side authorization, which the API tests own |
| HTTP client | `api-client.test.ts` | Request shape, credentials, JSON parsing, backend detail mapping, network failure, 204 | Live CORS and cookie behavior |
| Speech request | `voice.test.ts` | Whole-audio POST path and body, credentials, backend detail mapping, network failure, abort signal, speakable plain text without truncation | UI state and audio playback |
| Streaming TTS HTTP endpoint | `tests/api/test_voice_stream.py` | SSE frame contract, session requirement, blank text, pre-stream 503, in-band error frame and `[DONE]` | Adapter internals and browser playback |
| Streaming TTS adapter | `tests/llm/test_tts_stream.py` | Upstream PCM16 chunk decoding, mid-stream failure mapping, isolated frame cache replay | HTTP framing and UI state |
| Streamed speech client | `voice-stream.test.ts` | Frame parsing, base64 to PCM16 samples, abort, in-band error frame | UI state machine and audio device |
| Answer read-aloud | `answer-speech.test.tsx` | First-frame playback, busy and Stop states, localized failure and retry, request cancellation, Web Audio source cleanup on unmount, one active answer | Real device latency and audio quality |
| Data mode | `data-mode.test.tsx`, `preview-isolation.test.tsx` | Live pages call the API; preview pages make no request | Runtime env parity |
| Preview URL entry | `preview-mode.test.ts` | Every documented `?preview` value enters the demo and selects the right page state; unknown values stay live | The Providers wiring from URL to state, which is compile-checked |
| Auth pages live | `auth-live.test.tsx` | Each form's request, success path, mapped errors, pending state, safe redirect, configured-domain check, and backend-validated fallback | Real mailbox delivery |
| Conversations | `conversations.test.tsx` | Sidebar list, empty state, error retry, expired-session redirect | Pagination (not implemented) |
| Chat live | `chat-live.test.tsx`, `replay.test.tsx` | History load, history-rendered work chain/thinking/sources/tool calls, live `data-sources` handling, the answer capsule, request body, progressive stream, stop, error cleanup, new-conversation navigation, failed-turn retry keeping the conversation id, request-time model badge, replay without a chat POST, replay of a turn with no persisted assistant message, unauthorized replay clearing the session | Real model latency |
| Page composition | `chat-page.test.tsx`, `auth-pages.test.tsx`, `knowledge-page.test.tsx`, `knowledge-organize.test.tsx`, `knowledge-search.test.tsx`, `knowledge-status.test.tsx`, `knowledge-preview.test.tsx`, `practice-page.test.tsx`, `builds-page.test.tsx`, `deadlines-page.test.tsx` | Missing regions, unlabeled controls, missing components, a menu item that should be disabled, a missing status style | Visual layout and CSS overflow |
| Document preview | `knowledge-preview.test.tsx` | Back arrow target, page controls and their bounds, the empty page jump field, the page and scroll switch and its pressed state, the chat options, the honest "content not injected" notice; the PDF renderer is mocked because jsdom has no canvas | Real PDF rendering and scroll tracking, which the agent-browser pass covers |
| App shell | `app-shell.test.tsx` | Nav that should not exist, collapsed logo, footer account menu and sign out, sidebar state restore, mobile sheet close, page title, focus move | Server rendering, visual transitions |
| Source pane | `source-pane.test.tsx` | Row order and targets, X close, resize bounds and keyboard steps, width persistence, default closed at width zero, open state and staggered rows | Pointer feel and CSS cursor |
| Source capsule | `source-capsule.test.tsx` | Counts, thumbnails, `+N`, aria state, toggle | Visual fit at long titles |
| Inline source markers | `citation-markers.test.tsx` | `[ref_n]` links showing only the number, bare `[n]` left as text, hover content, unknown tokens, ordinary links untouched | Model compliance with paragraph-end placement |
| Preview role escape | `preview-controls.test.tsx` | Signed-out dead end, safe `next` handling, instructor/student destination choice | Real authentication |
| Interaction | The page tests, driven by user events | Capsule to pane, marker to source, work-chain expansion, retry, code confirmation, model choice | Network behavior |
| Translation completeness | `i18n.test.tsx` | Missing keys in one language, stale `lang` attribute | Translation quality |
| Markdown | `markdown.test.tsx`, `citation-markers.test.tsx` | Math and code plugins not applied; a citation marker is not linked to its source | Visual fidelity |
| Preview isolation | `preview-isolation.test.tsx` | A preview page calling the network (preview mode only) | Live API contract |
| Static serving | `tests/api/test_openapi_contract.py` | Browser deep link no longer returning the shell | Frontend routing |
| Chat HTTP contract | `tests/api/test_chat_stream.py`, `test_replay.py` | Frame order, thinking level and resolved selection in the trace meta, conversation id on failure, error frames in the trace | Browser rendering |

The static-serving test is a characterization guard for behavior that already exists. It does not count as a red, green slice.

## Build and serve

```bash
cd src/verifiable_tutor/ui/web
npm ci
npm run typecheck
npm run test
npm run build
```

The build writes `src/verifiable_tutor/ui/static/`. The backend checks for `index.html` when it starts, so build before starting the backend. `npm run dev` serves the SPA on the Vite port and proxies `/api` to `127.0.0.1:8000`.

`npm run build` builds the live app. `VITE_PREVIEW=1 npm run build` builds the offline preview demo instead; the same demo is available from a live build with `?preview=1`.

From the repository root, `./start.sh` runs the documented path in one command: it installs UI dependencies when the lockfile is newer, builds, and starts the backend. `./start.sh --dev` runs Vite beside the backend, `--no-build` reuses the last build, `--preview` builds the offline preview demo, and `--port` changes the backend port.

A fresh checkout has no `static/` directory. The build creates it, Git ignores it, and the API works without it. The directory does not hold a `.gitkeep`: it is generated output, not a scaffold directory.

## Language and accessibility

The UI ships English and Chinese resources with a header switch. The switch updates the `lang` attribute and persists the choice. The default is English. Controls are keyboard reachable and carry labels; the main flows meet the readability target in NFR-9. The theme is light only; the shadcn design tokens keep a dark theme possible later.

Each page sets `document.title` from its page name, and a client-side navigation moves focus to the `main` region. Labelled groups that are plain `div`s carry an explicit `role="group"`, and disabled controls that have no other explanation carry a title. The chat composer ignores Enter while an IME composition is active.

## Browser acceptance

jsdom cannot check real layout, real `fetch`, real PDF rendering, or menu and focus behavior, so the knowledge-base work ends with a browser pass driven by `agent-browser` against the built SPA on `http://127.0.0.1:8000`.

Preparation: a local QA instructor account is seeded with a password generated for that run and kept only in the shell that runs the check; screenshots go under the ignored `data/caches/qa/screenshots/`. The CLI's own workflow is read first with `agent-browser skills get core`, and the exploratory pass follows `agent-browser skills get dogfood`.

The pass walks these steps and asserts the visible result of each, taking a screenshot:

1. An anonymous visit to `/knowledge` redirects to `/login?next=/knowledge`; signing in returns to the page.
2. The root shows the twelve file tiles with real first-page thumbnails; the accessibility snapshot names each tile.
3. A search for a course term groups the results by document, names the match reason, shows the page number, and marks the words; an absent term shows the empty result state.
4. A Chinese search term matches, so the mixed-script path works.
5. Selecting a file fills the right pane with the name, dates, Qwen summary, page count, and chunk count.
6. The `+` menu opens with the upload item disabled and the folder item working; a new folder appears in the grid.
7. Moving a file into the new folder changes the breadcrumb; the move dialog refuses a folder's own descendant.
8. Dragging a file over the grid shows the overlay and issues no request.
9. The ellipsis menu opens, does not select the tile, and is reachable by Tab; deleting a file asks for confirmation and the tile disappears.
10. Double-clicking a file changes the URL to the document route, renders the first page on the canvas, and shows `1 / N`.
11. Previous, next, PageDown, and the page input all change the page; the browse switch turns single-page view into a continuous column, a page jump scrolls to that page, scrolling updates the indicator and the URL, and the back arrow returns to the originating folder.
12. The chat pane sends with `document_context`, the answer arrives, and the "document content not injected yet" notice is visible.
13. A reload restores language, sidebar state, pane width and collapse, composer selection, the document page, and the browse mode.
14. A narrow viewport turns the right pane into a sheet and the grid into one column.
15. A keyboard walk confirms focus order (each tile's open button, then its actions button), visible focus rings, and Esc closing menus and sheets.

Results of the 2026-11-05 pass, run with agent-browser 0.23.0 against the built SPA on `http://127.0.0.1:8000` with a locally seeded QA instructor account: steps 1 to 5, 6 (create), 7 (move), 8, 9, 10, 11, 12, 13, 14, and 15 passed against the seeded `course_project` and the nine single-page smoke documents. The real thumbnails, the full 342-page corpus, the vectors, and the twelve Qwen summaries arrive with the TACC ingestion, so step 2's thumbnail and step 5's summary are verified again after that run. Defects the pass found were fixed and covered by tests: the preview chat wiped the answer when the backend assigned a conversation id, the tile menu overlapped the name, an empty folder showed a blank pane, a page box holding letters wrote `NaN` into the URL, and the file pane did not restore its collapsed state.

A failure found here is first reproduced by a failing unit or API test, then fixed, then the checklist is rerun. The final results and screenshots are recorded in this section with the agent-browser version, the port, and the date.

## Milestone boundary

Milestone 3 adds the live knowledge-base browser and the document preview on top of milestone 2's authentication, history, streaming, and replay. Milestone 2 content stays as described above. The knowledge-base browser and the preview call the local API; the offline preview demo still hosts the fixture pages.

Still on preview structures: verified citations and page highlights, the practice code-execution job, the knowledge-base builds page, the deadline registry, and voice input and audio attachments. Practice generation, saved sessions, attempt paging, autosave, and grading call the local API. The work chain, thinking, model profile, numbered sources, and tool calls persist with each answer and render from the history response; the typed tool runner emits and persists tool calls, and `data-sources` carries the numbered sources. The source pane lists retrieved sources; it does not claim they are verified. Follow-ups that the backend does not support yet: span verification and claim support, chunk injection into the chat prompt, the upload chain, the `downloading` build state, and the deadline registry endpoint. The PRD requirements that depend on them are [FR-B3](prd.md), [FR-B4](prd.md), [FR-K1](prd.md), and [FR-A5](prd.md); the source pane requirement is [FR-B5](prd.md).
