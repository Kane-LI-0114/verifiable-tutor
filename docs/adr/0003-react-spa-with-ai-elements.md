# ADR-0003: React single-page UI with shadcn AI Elements

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-28 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The course requires a browser interface for task input, visible progress, and review of the result. The project additionally needs streaming answers, markdown with formulas and code, inline citations that open a page image, an evidence panel, Chinese and English text, and a replay mode that works offline. The demo should look like a current chatbot product.

Evidence collected on 2026-10-28:

- Mainstream chatbot products are React: OpenAI and Anthropic job posts ask for React and Next.js, Perplexity asks for React and Next.js, and the DeepSeek web client is a plain React SPA by bundle inspection.
- Open WebUI is the closest architectural precedent: a FastAPI backend serving a static SPA.

The platform offers no Node runtime, so the frontend must build on the laptop and ship as static assets. The team is more familiar with Vue than React, which is a cost to weigh, not a blocker.

## Decision

We build the UI as a React 19 single-page application with Vite, TypeScript, Tailwind CSS 4, shadcn/ui components copied into the repository, and AI Elements components for chat primitives: message scroller, message bubbles, a trace and task timeline, inline citation chips, a sources list, code blocks, and a prompt input. Markdown rendering uses streamdown with its math and code plugins, KaTeX, and Shiki. UI state for streaming uses `@ai-sdk/react` `useChat`.

The backend implements the AI SDK UI message stream protocol (version 1) in FastAPI. The adapter forwards `start`, `text-start`, `text-delta`, `text-end`, `data-step` for the progress timeline, `source-document` for citations, `finish`, and `error` chunks. The same chunks are recorded to JSONL for replay, and replay re-emits them at a speed factor, so replay exercises the production frontend path.

FastAPI serves the built assets on the same origin as the API. The build runs locally with `npm ci && npm run build` and writes to `src/verifiable_tutor/ui/static/`, which is generated and ignored by Git. `package-lock.json` is committed. No CDN is used: KaTeX fonts are self-hosted and the CJK text uses the system font stack.

The citation panel shows a server-rendered page WebP with absolutely positioned highlights from the OCR block boxes. It does not ship a PDF viewer.

## Consequences

**Positive:**
- Ready components cover the parts that distinguish the demo: step timeline, citation chips, sources panel, code blocks, streaming markdown.
- The stack is MIT or Apache-2.0, copy-in where possible, with no runtime lock-in.
- One origin, static assets, and no CDN keep the local demo and replay on one origin; SSH forwarding is not supported ([ADR-0011](0011-tacc-as-required-model-serving-backend.md)).
- The protocol adapter is shared with replay, so the offline demo uses the production UI code path.

**Negative:**
- React is new to the team. The estimate is two person-days of ramp-up, and a Vue stack would have none.
- The frontend adds a Node toolchain to local development and a build step before every upload; the build output is not committed.
- AI Elements is young and recently moved into shadcn, so component APIs may change; the copy-in model contains that risk but also means manual updates.
- The UI message stream adapter is project code to maintain and version; it is a small but real compatibility surface.
- No server-side rendering, which is acceptable for a single-user demo but means no shareable URLs with pre-rendered state.

**Neutral:**
- The frontend source lives inside the Python package tree; the repository layout must mark source and build output separately.

## Alternatives considered

**Vue 3 + Vite + Nuxt UI 4.** For: no ramp-up for the team, real chat components (ChatMessages, ChatReasoning, ChatTool), MIT, active. Against: no inline citation, sources, or trace primitives, so the three most distinctive parts of this project would be hand-built, about five person-days more. Why not chosen: the mainstream look and the ready components are the point; the ramp is cheaper than the missing components.

**Jinja2 templates with HTMX.** For: no Node, no build, smallest operational surface. Against: the target look and the streaming citation interactions would be hand-built. Why not chosen: does not meet the visual goal at acceptable cost.

**Next.js.** For: matches what OpenAI and Anthropic use and gives server components. Against: needs a Node server at runtime, which the platform lacks. Why not chosen: violates the deployment constraint.

**assistant-ui runtime.** For: ChatGPT-level interaction depth (threads, regenerate, edit, cancel) out of the box. Against: an extra 0.x runtime abstraction to customise for steps and citations. Why not chosen: the shadcn and AI SDK path is thinner and the interaction depth is not required for the demo; kept as an option if the demo needs branching conversations.

## References

- AI Elements in shadcn: https://ui.shadcn.com/docs/ai-elements
- AI SDK UI message stream protocol: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
- Open WebUI, FastAPI plus static SPA precedent: https://github.com/open-webui/open-webui
- OpenAI job post listing React and Next.js: https://jobs.ashbyhq.com/openai/ca54cd23-2bcc-4327-bcb6-46d81ed414a8
- Anthropic job post listing React and Next.js: https://job-boards.greenhouse.io/anthropic/jobs/5026097008
- Perplexity job post listing React and Next.js: https://jobs.ashbyhq.com/perplexity/78675022-c4a7-41d2-9259-7c59be4de93c
- Verification items: [../tech-selection.md](../tech-selection.md#verification-spikes)
