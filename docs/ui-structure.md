# Browser UI structure

| | |
|---|---|
| **Status** | Milestone 1, structure implemented |
| **Date** | 2026-11-03 |
| **Scope** | Routes, layout regions, the components each page uses, states, and the boundary between the preview build and live wiring |
| **Owner** | This file owns the page structure. [ADR-0003](adr/0003-react-spa-with-ai-elements.md) owns the frontend stack, [prd.md](prd.md) owns the behavior, and [tech-selection.md](tech-selection.md#ui-and-streaming-protocol) owns the build and serving decisions |

The UI source lives under `src/verifiable_tutor/ui/web/`. The build writes to `src/verifiable_tutor/ui/static/`, which Git ignores; the backend serves that directory on the same origin as the API ([factory.py](../src/verifiable_tutor/api/factory.py)). The first milestone fixes the page structure and uses preview data. It does not call the API, stream a real answer, or show verified citations.

## Page map

| Route | Access | Purpose | Data in milestone 1 |
|---|---|---|---|
| `/login` | Public | Sign in with email and password | Preview form |
| `/register` | Public | Register with a student email and password | Preview form |
| `/verify?email=` | Public | Confirm the six digit code | Preview form |
| `/reset` | Public | Request a password reset link | Preview form |
| `/reset/confirm?token=` | Public | Set a new password from the link | Preview form |
| `/chat` | Signed in | Start a new conversation | Preview fixture |
| `/chat/:sessionId` | Signed in | Conversation, work chain, citations, evidence panel; `?replay=1` shows the replay banner | Preview fixture |
| `/practice` | Signed in | Practice lab and self-test, with a "My solution" tab | Preview fixture; the run action shows the documented 503 state |
| `/knowledge` | Signed in | Browse knowledge cards, with a detail sheet | Preview fixture |
| `/instructor/builds` | Instructor | Start and watch a Qwen knowledge-base build | Preview fixture |
| `/instructor/deadlines` | Instructor | Read the deadline registry state | Preview fixture; the backend has no registry endpoint yet |
| `*` | Public | Not found | None |

Authentication routes render in a centered column without the application shell. Every other route renders inside the shell. The instructor routes are nested under the same navigation group as the student routes, but their menu entries are hidden for a student and the route guard renders the forbidden page for a student.

## Layout regions

```text
┌───────────────────────────────────────────────────────────────┐
│ Top bar: brand, page title, language switch, user menu        │
├───────────────┬───────────────────────────────┬───────────────┤
│ Sidebar       │ Thread                        │ Evidence      │
│ New question  │ Work chain                    │ Page number   │
│ Chat          │ Reasoning                     │ Page image    │
│ Practice      │ Markdown and citations        │ Highlight box │
│ Knowledge     │ Sources, tool calls, code     │ Quoted span   │
│ Instructor    │ Composer                      │ Empty state   │
│ Conversations │                               │               │
└───────────────┴───────────────────────────────┴───────────────┘
```

On a narrow viewport the sidebar becomes a sheet and the evidence panel opens as a sheet from a citation chip. The other pages use one centered column with a page header.

The authentication pages use two columns on a wide viewport: product framing on the left and the form card on the right. A narrow viewport shows only the form card.

## Page composition

### Chat

| Region | Components | Notes |
|---|---|---|
| Thread | Message Scroller, Message, Bubble, Markdown | The user turn is a bubble; the assistant turn is a flat column |
| Work chain | Trace, Task, Badge | Steps: understand, retrieve, verify, decide, generate, cite. The decide step shows the policy state |
| Thinking | Reasoning | Collapsed by default |
| Answer | Markdown with the math and code plugins | Formulas through KaTeX, code through Shiki |
| Citations | Inline Citation, Sources | A chip opens the evidence panel. Citations sit in a row after the answer in milestone 1; inline placement in prose arrives with the `source-document` frames |
| Tool calls | Tool, Terminal, Code Block | Exact command line, exit code, truncated output |
| Actions | Button, Tooltip | Copy, retry, speak. The speak action uses a button and an audio element |
| Composer | Input Group, Model Selector, Attachment | Provider and tier, thinking level, audio attachment (MiMo only), microphone control, send and stop |

The model selector offers DeepSeek Flash, MiMo Flash, and MiMo Pro, plus the four thinking levels. An audio attachment with DeepSeek selected renders the capability error instead of sending.

### Evidence panel

The panel shows the document id, the page number, previous and next page controls, the page image, highlight rectangles, and the quoted span. It uses the real image URL `/api/corpus/<doc_id>/pages/<page_no>.webp` and a placeholder frame in the preview build. Highlight rectangles come from `bbox_norm`, a normalized `[x1, y1, x2, y2]` box from [corpus-schema.md](corpus-schema.md). The panel must not claim that a span is verified until the deterministic verifier supplies that result.

### Practice and self-test

The page has two tabs. "Questions" holds the topic and type controls, the generated question, the answer form, the run state, and the grading result. "My solution" holds the pasted solution and the line-anchored explanation structure. The five question types are single choice, multiple choice, true or false, short answer, and code. Choice answers use Radio Group or Checkbox, short answers use Textarea, and code answers use a text area plus a read-only Code Block. A Confirmation step precedes any user code execution. Test Results renders the recorded suites and failures. The grading result carries its citations.

### Knowledge base

The page has a search field, a document filter, a card grid, and pagination. A card shows the summary, key terms, page number, study question count, and citation count. Selecting a card opens a sheet with the full summary, key terms, study questions, and citations. The "use in a review outline" action opens the chat page with a prefilled prompt.

### Knowledge-base builds

Instructors get a build list and a new-build dialog with the document id and the chunk limit. A build row shows the state, job id, record count, and timestamps. The detail view shows the state timeline, the request JSON, and the failure message with a retry action. Milestone 1 uses the four states the backend defines: `queued`, `running`, `ready`, and `failed`. The PRD also asks for a `downloading` state; the backend does not emit it yet and the UI does not invent it.

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

The chat page wires Message Scroller, the message composition, and the composer together. It does not copy the documentation demos, which depend on a fake transport, `motion`, and Next.js helpers. Not every pattern needs its own file: model selection and confirmation are small compositions inside the page that uses them.

Not used in milestone 1: Plan, Context, Chain of Thought, Questionnaire, the audio player and speech input patterns (built from a button and a native element), and animation. The streaming state comes from a `useTutorChat` seam. Milestone 2 replaces its preview implementation with `@ai-sdk/react` `useChat` without changing the pages.

## States and preview mode

Every page renders loading, empty, error, and forbidden states. The shell redirects an unauthenticated visitor to `/login?next=`. In the preview build, `?preview=loading`, `?preview=empty`, and `?preview=error` select a state, and the developer controls switch between signed out, student, and instructor. `?previewRole=instructor` selects a role on first load, and the choice persists in local storage so a reviewer can move between pages.

The preview build makes no API request. `VITE_PREVIEW=0` disables the preview data at build time; the live wiring is milestone 2.

## Data contracts and coverage

The TypeScript types in `src/verifiable_tutor/ui/web/src/lib/types.ts` mirror the JSON the backend returns. They do not add fields the backend does not have.

| Surface | Endpoint | Backend state | Milestone 1 |
|---|---|---|---|
| Registration, verification, login, logout, reset | `/api/auth/*` | Implemented | Preview form |
| Current account | `/api/auth/me` | Implemented | Preview account |
| Conversations and history | `/api/sessions`, `/api/sessions/{id}/messages` | Implemented | Fixture |
| Chat stream | `POST /api/chat` | Implemented, one `data-step` for generate | Fixture with six work-chain steps |
| Citations and highlights | `source-document` frames, page block coordinates | Missing | Structure only |
| Practice run | `POST /api/practice/runs` | Documented 503 | Unavailable state |
| Knowledge cards | `GET /api/knowledge/cards` | Implemented | Fixture |
| Knowledge builds | `GET` and `POST /api/knowledge/builds` | Implemented, no downloading state | Fixture with four states |
| Deadline registry | None | Missing | Read-only fixture |
| Voice | `/api/voice/*` | Implemented | Control structure |
| Page image | `/api/corpus/{doc_id}/pages/{page_no}.webp` | Implemented | Real URL, placeholder frame |

## TDD seams

The UI follows the red, green, refactor loop at these seams. The tests live in `src/verifiable_tutor/ui/web/tests/`.

| Seam | Test | Catches | Misses |
|---|---|---|---|
| Routes and guards | `router.test.tsx` | Default route, unauthenticated redirect, role leak, unknown path | Server-side authorization, which the API tests own |
| Page composition | `chat-page.test.tsx`, `auth-pages.test.tsx`, `knowledge-page.test.tsx`, `practice-page.test.tsx`, `deadlines-page.test.tsx` | Missing regions, unlabeled controls, missing components | Visual layout and CSS overflow |
| Interaction | The page tests, driven by user events | Citation to panel, work-chain expansion, retry, code confirmation, model choice | Network behavior |
| Translation completeness | `i18n.test.tsx` | Missing keys in one language, stale `lang` attribute | Translation quality |
| Markdown | `markdown.test.tsx` | Math and code plugins not applied | Visual fidelity |
| Preview isolation | `preview-isolation.test.tsx` | A preview page calling the network | Live API contract |
| Static serving | `tests/api/test_openapi_contract.py` | Browser deep link no longer returning the shell | Frontend routing |

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

A fresh checkout has no `static/` directory. The build creates it, Git ignores it, and the API works without it. The directory does not hold a `.gitkeep`: it is generated output, not a scaffold directory.

## Language and accessibility

The UI ships English and Chinese resources with a header switch. The switch updates the `lang` attribute and persists the choice. The default is English. Controls are keyboard reachable and carry labels; the main flows meet the readability target in NFR-9. The theme is light only; the shadcn design tokens keep a dark theme possible later.

## Milestone boundary

Milestone 1 fixes the structure and proves the documented components render in their intended places. Milestone 2, the live wiring, covers the authentication flows, conversation history, `useChat` streaming, citation and highlight frames from the evidence layer, the practice execution job, the deadline editor, voice input and playback, and real API error and loading states.

Follow-ups that the backend does not support yet: `source-document` frames, block coordinates in an HTTP response, the `downloading` build state, and the deadline registry endpoint. The PRD requirements that depend on them are [FR-B3](prd.md), [FR-B5](prd.md), [FR-K1](prd.md), and [FR-A5](prd.md).
