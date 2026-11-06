# Browser UI structure

| | |
|---|---|
| **Status** | Milestone 3, authentication and chat wired to the local API; the knowledge-base browser and PDF preview are in progress |
| **Date** | 2026-11-05 |
| **Scope** | Routes, layout regions, the components each page uses, states, and the boundary between live data and the offline preview demo |
| **Owner** | This file owns the page structure. [ADR-0003](adr/0003-react-spa-with-ai-elements.md) owns the frontend stack, [prd.md](prd.md) owns the behavior, and [tech-selection.md](tech-selection.md#ui-and-streaming-protocol) owns the build and serving decisions |

The UI source lives under `src/verifiable_tutor/ui/web/`. The build writes to `src/verifiable_tutor/ui/static/`, which Git ignores; the backend serves that directory on the same origin as the API ([factory.py](../src/verifiable_tutor/api/factory.py)). Milestone 2 wires the authentication flows, the server-side session, conversation history, streamed chat, and replay to the local API. Citations, page images, practice, the knowledge base, the deadline registry, and voice still use preview structures; the evidence layer and the OCR corpus arrive in a later milestone.

## Page map

| Route | Access | Purpose | Data source |
|---|---|---|---|
| `/login` | Public | Sign in with email and password | Live API, preview in demo mode |
| `/register` | Public | Register with a student email and password | Live API, preview in demo mode |
| `/verify?email=` | Public | Confirm the six digit code | Live API, preview in demo mode |
| `/reset` | Public | Request a password reset link | Live API, preview in demo mode |
| `/reset/confirm?token=` | Public | Set a new password from the link | Live API, preview in demo mode |
| `/chat` | Signed in | Start a new conversation | Live empty thread |
| `/chat/:sessionId` | Signed in | Conversation, work chain, citations, collapsible evidence panel; `?replay=1` replays the recorded trace | Live history and stream; replay trace |
| `/practice` | Signed in | Practice lab and self-test, with a "My solution" tab | Preview fixture; the run action shows the documented 503 state |
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
│ Sidebar       │ Thread                        │ Evidence      │
│ Logo          │ Work chain                    │ Resize handle │
│ New question  │ Reasoning                     │ Page number   │
│ Practice      │ Markdown and citations        │ Page image    │
│ Knowledge     │ Sources, tool calls, code     │ Highlight box │
│ Instructor    │ Composer                      │ Quoted span   │
│ Conversations │                               │ Empty state   │
│ Account menu  │                               │               │
└───────────────┴───────────────────────────────┴───────────────┘
```

The sidebar has no separate Chat entry: New question opens an empty conversation and the conversation list opens an existing one. The sidebar collapses to a 48px icon rail; in that state only the logo, the nav icons, and the account avatar remain, and the account name is reachable through the avatar menu. The account menu and sign out live in the sidebar footer, not in the top bar.

On a narrow viewport the sidebar becomes a sheet that closes when a destination is chosen, and the evidence panel opens as a sheet from a citation chip. The other pages use one centered column with a page header.

The authentication pages use two columns on a wide viewport: product framing on the left and the form card on the right. A narrow viewport shows only the form card. The authentication pages and the not-found page render without the shell but keep the language switch and the preview controls in the top right corner, so a reviewer can always change role or language.

## Page composition

### Chat

| Region | Components | Notes |
|---|---|---|
| Thread | Message Scroller, Message, Bubble, Markdown | The user turn is a bubble; the assistant turn is a flat column |
| Work chain | Trace, Task, Badge | Steps: understand, retrieve, verify, decide, generate, cite. The steps render as a compact chip row in the header, in canonical phase order; each chip's title carries its duration, detail, policy, and rule id, and the header badge shows the policy state. The expanded chain contains only the ordered work-chain events: each reasoning segment immediately before the tool calls it preceded |
| Thinking | Reasoning block inside the work chain | Each model call's reasoning is a work-chain event and renders before the tool calls of that call; there is no separate thinking section |
| Answer | Markdown with the math and code plugins | Formulas through KaTeX, code through Shiki |
| Citations | Inline Citation, Sources | A chip opens the evidence panel and expands it if it was collapsed. Citations sit in a row after the answer; fresh answers have none until the evidence layer emits `source-document` frames, and inline placement in prose arrives with them |
| Tool calls | Tool, Terminal, Code Block | Inside the work chain, in event order, not at the end of the answer bubble: tool name, arguments, result summary, duration, optional command line and exit code, truncated output |
| Actions | Button, Tooltip | Copy, retry, speak. The speak action uses a button and an audio element |
| Composer | Input Group, Model Selector, Attachment | Provider and tier, thinking level, audio attachment (MiMo only), microphone control, send and stop. Enter sends, Shift+Enter inserts a newline, and Enter during an IME composition confirms the candidate instead of sending. The model and thinking choice persists in browser local storage (`vt.composer.selection`), so a refresh or another conversation keeps the last choice; missing or invalid stored data falls back to DeepSeek Flash with thinking off |

The model selector offers DeepSeek Flash, MiMo Flash, and MiMo Pro. DeepSeek exposes the four thinking levels; MiMo exposes only Off and On, the request carries `on`, and the adapter maps it to MiMo's `{"type": "enabled"}`. Switching to MiMo clamps a stored `low`, `high`, or `max` selection to On. All three values are sent with the live turn. In live mode the audio attachment and microphone controls stay disabled until the voice wiring lands; the preview demo keeps the attachment state and the DeepSeek capability error.

Changing the route from `/chat` to `/chat/:sessionId`, or to another session, remounts the conversation state and loads that conversation's history from `GET /api/sessions/{id}/messages`; `/chat` always starts empty. The conversation a finished first answer opens loads the same way, because the backend persists each answer's turn metadata with the answer; the work chain, thinking, citations, and tool calls therefore survive the remount and every later reload. When the conversation is non-empty, a visually hidden `h1` names the conversation. Each live conversation also remembers its thread scroll position in browser local storage (`vt.chat.scroll.<sessionId>`), so reopening it or switching back restores the reading position; a conversation opened for the first time, replay, and the preview demo keep the default end position. The page keeps the last twenty loaded histories in memory for the signed-in user and warms them from the conversation list, so switching to a listed conversation renders from that cache while it revalidates, without flashing the loading state; the cache is dropped on sign-out, and sending a turn in a conversation drops its entry so the next visit reloads the stored history. The preview demo carries one seeded conversation per fixture session instead.

In live mode the chat state comes from `@ai-sdk/react` `useChat` with the project transport (`src/verifiable_tutor/ui/web/src/lib/chat/tutor-transport.ts`). The transport sends only the newest user text plus `session_id`, `provider`, `tier`, and `thinking` to `POST /api/chat`, because the backend owns the conversation history. The conversation id arrives in the `x-conversation-id` response header; a new conversation navigates to `/chat/<id>` after the stream finishes and the answer with its turn metadata is persisted. When a turn fails before the stream starts, the client keeps the conversation id from the same header, so a retry sends the question into that conversation instead of creating a second one. The streamed answer carries the request-time provider and tier as message metadata, so its badge does not follow a later composer change. A live work chain derives its step chips from the `data-step` custom data parts; reasoning text from `reasoning-*` frames and live tool calls from `data-tool` parts are composed into ordered work-chain events, which are the only content of the expanded chain; a stored turn renders the persisted step chips, ordered events, citations, and tool calls that the history response returns, through the same components. A stream failure stops the answer, drops the partial text, shows the failure copy, and offers to put the question back in the composer; it is never replayed as if complete (FR-B12). Replay re-emits the recorded trace through the same components at a selectable speed, and the composer is hidden while replays run.

### Evidence panel

The panel shows the document id, the page number, previous and next page controls, the page image, highlight rectangles, and the quoted span. It uses the real image URL `/api/corpus/<doc_id>/pages/<page_no>.webp` and an explicit preview notice instead of a fake loading frame; the notice says the page image is not included in the preview build rather than printing the raw API URL. The corpus mirror under `data/corpus/images/` is empty until the OCR pipeline produces it, so the live image path degrades to the not-found notice. Highlight rectangles come from `bbox_norm`, a normalized `[x1, y1, x2, y2]` box from [corpus-schema.md](corpus-schema.md). The panel must not claim that a span is verified until the deterministic verifier supplies that result.

On a wide viewport the panel can be collapsed and resized. The default width is 380px, the minimum is 280px, and the maximum is `min(640px, 55% of the viewport)`. The drag handle on the panel's left edge uses `cursor: col-resize` and pointer capture; the same handle is a focusable separator with `aria-valuenow`, `aria-valuemin`, and `aria-valuemax`, arrow-key resizing in 16px steps, and Home/End for the bounds. A double click resets the width to 380px. Collapsing leaves a 44px rail with a labelled expand button, and the collapsed state plus the width persist in local storage (`vt.evidence.width`, `vt.evidence.collapsed`). Opening a citation from a collapsed state expands the panel.

### Practice and self-test

The page has two tabs. "Questions" holds the topic and type controls, the generated question, the answer form, the run state, and the grading result. "My solution" holds the pasted solution and the line-anchored explanation structure. The five question types are single choice, multiple choice, true or false, short answer, and code. Choice answers use Radio Group or Checkbox, short answers use Textarea, and code answers use a text area plus a read-only Code Block. A Confirmation step precedes any user code execution. Test Results renders the recorded suites and failures. The grading result carries its citations.

### Knowledge base

The page is a file browser over the local corpus ([ADR-0015](adr/0015-local-knowledge-store-and-chunking.md)). It has three regions inside the shell's main column, the same flex row the chat page uses: a header band, a tile grid, and a right-hand file pane.

The header band holds the breadcrumb, the search field, and a round `+` button. The breadcrumb starts at the root and lists every ancestor folder; each segment is a button that navigates to that folder. The `+` menu has two items: "Upload file", which is disabled with a title explaining that the TACC upload chain is not verified yet, and "New folder", which opens a naming dialog. The whole grid is a drop target that shows an overlay when files are dragged over it and refuses the drop with the same explanation; no request is made.

The grid shows folders first and files after them. A folder tile is a folder glyph with the folder name; a file tile is the rendered first page of the PDF as its icon, the file name (two lines maximum), its status, and a metadata line. Selecting a tile fills the right pane without leaving the page; double-clicking a file opens the document route. Both tile kinds carry an ellipsis button at the bottom right of the icon area with a 24px hit area: a folder offers "Move folder" and "Delete folder" (deleting the documents inside it), and a file offers "Move file" and "Delete file". The ellipsis is a separate button, so it never selects or opens the tile, and it is reachable by Tab. Delete actions use a confirmation dialog; the folder dialog names how many files it contains. Move actions use a folder-tree dialog that refuses to move a folder into itself or a descendant.

The file status is shown on the tile and in the right pane. `uploading` dims the icon with a progress indicator, `uploaded` and `processing` show a skeleton with a spinner, `upload_failed` and `failed` show a failure badge whose title carries the reason, and `ready` shows nothing.

Searching replaces the grid with a flat result list grouped by document. Each result names why it matched (file name, folder, page text, or summary), shows the page number for a text hit, and marks the matched words in the snippet. The highlight ranges come from the API, not from a second client-side match, so the marking and the match cannot disagree.

The right pane is the same width, position, and drag behavior as the chat page's evidence pane. It shows the file name, the date it was added, the Qwen summary and the model that wrote it, the page and chunk counts, the localized document status, and a collapsed knowledge-card section fed by `GET /api/knowledge/cards?doc_id=`. With no selection it explains what selecting a file does. Below 1024px the pane is a sheet that opens on selection.

### Document preview

The document route replaces the whole knowledge-base region, not a dialog. The left side is the PDF page rendered on a canvas; the header carries a back arrow that returns to the folder the reader came from, the file name, the page indicator, previous and next buttons, and a page input. PageUp and PageDown move one page. Only one page is rendered at a time; there is no continuous scroll.

The right pane on this route is a conversation, not the file record: it has the message list, the same composer as the chat page (provider, tier, and thinking level persist through `vt.composer.selection`), and it sends `document_context` with `doc_id` and the current page so the answer knows what is open. Below 1024px a button in the header opens the same conversation as a sheet. Until the citation and context-injection stage lands, the answers do not contain the document text and the pane says so at the top. The conversation is created on the first send and its id is remembered per document in browser local storage.

### Knowledge-base builds

Instructors get a build list and a new-build dialog with the document id and the chunk limit. A build row shows the state, job id, record count, and timestamps. The detail view shows the state timeline, the request JSON, and the failure message with a retry action. The preview page uses the four states the backend defines: `queued`, `running`, `ready`, and `failed`. The PRD also asks for a `downloading` state; the backend does not emit it yet and the UI does not invent it.

### Deadline registry

Instructors get a read-only table of assignments with release date, due date, extension window, and the five policy states (`pre-release`, `active`, `extension-window`, `post-deadline`, `unknown`), plus the registry version and the injected clock. An unknown state shows the fail-closed notice. The in-app editor is P1 and the page says so. The backend has no registry endpoint yet.

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
| Trace and task timeline | `components/ui/trace.tsx`, `components/chat/work-chain.tsx` | shadcn registry plus a composition |
| Inline citation | `components/chat/citation-row.tsx` | shadcn hover card and button |
| Sources | `components/chat/sources.tsx` | composition on trace |
| Code block | `components/ui/code-block.tsx` | shadcn registry |
| Prompt input | `components/ui/input-group.tsx`, `components/ui/attachment.tsx`, `components/chat/composer.tsx` | shadcn registry plus a composition |
| Model selector | inside `components/chat/composer.tsx` | composition on dropdown menu and input group |
| Tool and terminal | `components/chat/tool-call.tsx` | composition on trace and code block |
| Reasoning | `components/chat/reasoning-trace.tsx` | composition on trace |
| Confirmation | the dialog in `routes/practice/practice-page.tsx` | composition on dialog and button |
| Test results | `components/practice/test-results.tsx` | composition on trace and code block |
| Markdown with math and code | `components/ai/markdown.tsx` | streamdown with the code, math, and CJK plugins, KaTeX CSS |

The live and preview chat pages render the shared session shell in `src/verifiable_tutor/ui/web/src/components/chat/chat-session-shell.tsx` (thread, evidence pane, narrow-screen evidence sheet, and replay banner) and each page keeps its own data access; together they wire Message Scroller, the message composition, and the composer. They do not copy the documentation demos, which depend on a fake transport, `motion`, and Next.js helpers. Not every pattern needs its own file: model selection and confirmation are small compositions inside the page that uses them.

Not used yet: Plan, Context, Chain of Thought, Questionnaire, the audio player and speech input patterns (built from a button and a native element), and animation. In live mode the streaming state comes from `@ai-sdk/react` `useChat` with the project transport; the preview demo keeps its fixture-based chat. Voice input and playback stay structured but unwired.

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
| Conversations and history | `/api/sessions`, `/api/sessions/{id}/messages` | Implemented: messages include persisted turn metadata (work steps, thinking, model profile, citations, tool calls) | Wired in milestone 2 |
| Chat stream | `POST /api/chat` | Implemented: `start-step` and `finish-step` per model call, `data-step` for generate and retrieve, `data-tool` for live tool activity, `x-conversation-id`, thinking level, the resolved model selection in the trace meta, and the persisted turn before the `finish` frame | Wired in milestone 2 |
| Tool calls | `data-tool` frames and `tool_calls` rows | Implemented: name, provider call id, arguments, structured result, output, duration, status | Wired: live frames and history |
| Replay | `GET /api/sessions/{id}/replay` | Implemented, recorded trace frames | Wired in milestone 2 |
| Citations and highlights | `source-document` frames and page block coordinates; chat citations are persisted in `citations` and returned by the history API once produced | Producer missing | Structure only |
| Practice run | `POST /api/practice/runs` | Documented 503 | Unavailable state |
| Knowledge cards | `GET /api/knowledge/cards` | Implemented | Wired: the file pane's collapsed card section |
| Knowledge folders and files | `GET/POST/PATCH/DELETE /api/knowledge/folders`, `GET/PATCH/DELETE /api/knowledge/documents` | Implemented | Wired in milestone 3 |
| Document PDF | `GET /api/knowledge/documents/{doc_id}/file` | Implemented | Wired: the preview fetches it once |
| Knowledge search | `GET /api/knowledge/search` | Implemented | Wired: search field and result list |
| Retrieval preview | `GET /api/knowledge/retrieve` | Implemented; the agent `search_course` tool calls the same hybrid retriever | Not used by a page; the agent loop uses the retriever directly |
| Knowledge builds | `GET` and `POST /api/knowledge/builds` | Implemented, no downloading state | Fixture with four states |
| Deadline registry | None | Missing | Read-only fixture |
| Voice | `/api/voice/*` | Implemented | Control structure |
| Page image | `/api/corpus/{doc_id}/pages/{page_no}.webp` | Implemented, corpus mirror empty | Real URL, explicit preview notice |

## TDD seams

The UI follows the red, green, refactor loop at these seams. The tests live in `src/verifiable_tutor/ui/web/tests/`.

| Seam | Test | Catches | Misses |
|---|---|---|---|
| Routes and guards | `router.test.tsx`, `live-session.test.tsx` | Default route, unauthenticated redirect, unavailable retry, role leak, unknown path | Server-side authorization, which the API tests own |
| HTTP client | `api-client.test.ts` | Request shape, credentials, JSON parsing, backend detail mapping, network failure, 204 | Live CORS and cookie behavior |
| Data mode | `data-mode.test.tsx`, `preview-isolation.test.tsx` | Live pages call the API; preview pages make no request | Runtime env parity |
| Preview URL entry | `preview-mode.test.ts` | Every documented `?preview` value enters the demo and selects the right page state; unknown values stay live | The Providers wiring from URL to state, which is compile-checked |
| Auth pages live | `auth-live.test.tsx` | Each form's request, success path, mapped errors, pending state, safe redirect, configured-domain check, and backend-validated fallback | Real mailbox delivery |
| Conversations | `conversations.test.tsx` | Sidebar list, empty state, error retry, expired-session redirect | Pagination (not implemented) |
| Chat live | `chat-live.test.tsx`, `replay.test.tsx` | History load, history-rendered work chain/thinking/citations/tool calls, request body, progressive stream, stop, error cleanup, new-conversation navigation, failed-turn retry keeping the conversation id, request-time model badge, replay without a chat POST, replay of a turn with no persisted assistant message, unauthorized replay clearing the session | Real model latency |
| Page composition | `chat-page.test.tsx`, `auth-pages.test.tsx`, `knowledge-page.test.tsx`, `knowledge-organize.test.tsx`, `knowledge-search.test.tsx`, `knowledge-status.test.tsx`, `knowledge-preview.test.tsx`, `practice-page.test.tsx`, `builds-page.test.tsx`, `deadlines-page.test.tsx` | Missing regions, unlabeled controls, missing components, a menu item that should be disabled, a missing status style | Visual layout and CSS overflow |
| Document preview | `knowledge-preview.test.tsx` | Back arrow target, page controls and their bounds, the chat options, the honest "content not injected" notice; the PDF renderer is mocked because jsdom has no canvas | Real PDF rendering, which the agent-browser pass covers |
| App shell | `app-shell.test.tsx` | Nav that should not exist, collapsed logo, footer account menu and sign out, sidebar state restore, mobile sheet close, page title, focus move | Server rendering, visual transitions |
| Evidence pane | `evidence-pane.test.tsx` | Collapse, resize bounds and keyboard steps, persistence, citation auto-expand, honest preview notice | Pointer feel and CSS cursor |
| Preview role escape | `preview-controls.test.tsx` | Signed-out dead end, safe `next` handling, instructor/student destination choice | Real authentication |
| Interaction | The page tests, driven by user events | Citation to panel, work-chain expansion, retry, code confirmation, model choice | Network behavior |
| Translation completeness | `i18n.test.tsx` | Missing keys in one language, stale `lang` attribute | Translation quality |
| Markdown | `markdown.test.tsx` | Math and code plugins not applied | Visual fidelity |
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
11. Previous, next, PageDown, and the page input all change the page; the back arrow returns to the originating folder.
12. The chat pane sends with `document_context`, the answer arrives, and the "document content not injected yet" notice is visible.
13. A reload restores language, sidebar state, pane width and collapse, composer selection, and the document page.
14. A narrow viewport turns the right pane into a sheet and the grid into one column.
15. A keyboard walk confirms focus order (each tile's open button, then its actions button), visible focus rings, and Esc closing menus and sheets.

Results of the 2026-11-05 pass, run with agent-browser 0.23.0 against the built SPA on `http://127.0.0.1:8000` with a locally seeded QA instructor account: steps 1 to 5, 6 (create), 7 (move), 8, 9, 10, 11, 12, 13, 14, and 15 passed against the seeded `course_project` and the nine single-page smoke documents. The real thumbnails, the full 342-page corpus, the vectors, and the twelve Qwen summaries arrive with the TACC ingestion, so step 2's thumbnail and step 5's summary are verified again after that run. Defects the pass found were fixed and covered by tests: the preview chat wiped the answer when the backend assigned a conversation id, the tile menu overlapped the name, an empty folder showed a blank pane, a page box holding letters wrote `NaN` into the URL, and the file pane did not restore its collapsed state.

A failure found here is first reproduced by a failing unit or API test, then fixed, then the checklist is rerun. The final results and screenshots are recorded in this section with the agent-browser version, the port, and the date.

## Milestone boundary

Milestone 3 adds the live knowledge-base browser and the document preview on top of milestone 2's authentication, history, streaming, and replay. Milestone 2 content stays as described above. The knowledge-base browser and the preview call the local API; the offline preview demo still hosts the fixture pages.

Still on preview structures: citation and highlight frames from the evidence layer, the practice execution job, the knowledge-base builds page, the deadline registry, and voice input and playback. The work chain, thinking, model profile, tool calls, and citations persist with each answer and render from the history response; the typed tool runner now emits and persists tool calls, so live answers show `retrieve` and tool activity as well as the generate step. The citation rows stay empty until the evidence layer produces verified spans. Follow-ups that the backend does not support yet: `source-document` frames, chunk injection into the chat prompt, citation persistence and span verification, the upload chain, the `downloading` build state, and the deadline registry endpoint. The PRD requirements that depend on them are [FR-B3](prd.md), [FR-B5](prd.md), [FR-K1](prd.md), and [FR-A5](prd.md).
