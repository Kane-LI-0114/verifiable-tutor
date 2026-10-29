# ADR-0008: LangGraph as the agent orchestration runtime

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-29 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

[docs/tech-selection.md](../tech-selection.md) chose a hand-written asyncio state machine with explicit budgets and rejected agent frameworks for their opaque control flow and implicit budgets. On 2026-10-29 the project lead decided that the agent must be built with LangGraph. This record replaces the earlier orchestration choice and the framework rejection.

The workflow must support:

- An explicit multi-step graph: intent and disclosure decision, retrieval, evidence verification, generation, citation checks, and the practice and teaching flows.
- Per-user conversation state that survives process restarts.
- Streaming of step progress, model thinking, and tool executions to the browser, because the course requires visible progress and the lead requires the agent's thinking and command execution to be visible.
- Human approval for commands that write files or run user supplied code.
- Testable seams and tracing hooks ([ADR-0007](0007-langfuse-for-local-model-call-tracing.md)).

LangGraph facts verified on 2026-10-29 from the published packages:

- `langgraph` 1.2.18 requires Python 3.10 or later and depends on `langchain-core` 1.x, `langgraph-checkpoint` 4.x, `langgraph-prebuilt` 1.x, `langgraph-sdk` 0.4.x, pydantic, and xxhash.
- `langgraph-checkpoint-sqlite` 3.1.2 persists state in SQLite and depends on aiosqlite and sqlite-vec.
- The framework provides typed `StateGraph`, persistence and checkpointers, streaming modes (updates, messages, custom, and event streams), interrupts for human in the loop, and a documented Langfuse LangChain callback integration.

Platform constraints from [ADR-0001](0001-pinned-python-environment-without-docker.md): the project layer is a hash-pinned install into `$HOME` inside one hour jobs, so every new dependency must be pinned, import-verified in the course public environment, and removed from the critical path if it fails.

## Decision

- LangGraph is the single orchestration runtime for the agent backend. The workflow is a typed `StateGraph` (or a small set of graphs), and the disclosure gate, retrieval, evidence verification, generation, citation checks, practice flow, and teaching flow are nodes rather than hand-rolled control flow.
- The graph is hosted inside the existing FastAPI process. No LangGraph Platform, LangGraph Server, or managed service is used.
- Conversation state is persisted with a checkpointer. The first implementation uses the SQLite checkpointer with one thread per user and session, and the database lives with the other state under the TACC `USERDIR` or its local mirror. If sqlite-vec fails in the course public environment, the fallback is the in-memory saver plus the application's own JSONL session store; the implementation change records which one shipped.
- LangGraph event streams are translated into the existing AI SDK UI message stream ([ADR-0003](0003-react-spa-with-ai-elements.md)): node transitions become step events, model reasoning becomes thinking events, tool calls and command output become tool events, and text deltas pass through. The same recorded event sequence powers replay.
- Instrumentation: in local development the LangChain callback handler sends graph and tool spans to Langfuse ([ADR-0007](0007-langfuse-for-local-model-call-tracing.md)). On TACC the callback is omitted and JSONL remains the trace source of truth.
- The model boundary stays in `src/verifiable_tutor/llm/`; LangGraph nodes call the existing adapter and do not use LangChain chat model wrappers for provider calls, so the retry, cache, audio, and search behavior from [ADR-0005](0005-external-model-apis-as-primary.md) and [ADR-0006](0006-same-model-retries-without-cross-model-fallback.md) stays in one place.
- Budgets (model calls, tool calls, context tokens, and wall time) stay in project code and are enforced at node boundaries, not delegated to framework settings.
- `langgraph`, `langchain-core`, and `langgraph-checkpoint-sqlite` are pinned exactly in `pyproject.toml` and `uv.lock`, and the same pins are added to `scripts/tacc/requirements-tacc.txt`. A TACC spike imports LangGraph and runs a two node graph before the dependency is relied on.

## Consequences

**Positive:**

- Explicit nodes and typed state make every step observable, testable, and replayable; the progress UI and the trace evidence map directly to graph events.
- Persistence, resume, streaming, and human in the loop come from the framework instead of project code.
- Langfuse integration is first class through the LangChain callback handler.
- The graph stays model-agnostic; the adapter remains the only provider boundary.

**Negative:**

- A large dependency group enters the project layer and must be hash-pinned and import-verified on TACC. The first job pays the install cost, and the native sqlite-vec extension may fail under the PRoot runtime.
- Framework API churn: the pinned versions of langgraph, langchain-core, and the checkpointer must move together.
- Framework abstractions can hide retries, budgets, and token accounting, so the project has to enforce them at the node boundary.
- The team must learn the framework, and debugging inside it is harder than in hand-written code.

**Neutral:**

- LangChain high-level agents and prebuilt ReAct graphs are not used; only StateGraph, checkpointing, interrupts, and streaming are adopted.

**Follow-up:**

- Define the graph topology and the state schema in the PRD and in `src/verifiable_tutor/orchestrator/`, with transition tests at the graph seam.
- Spike LangGraph plus the SQLite checkpointer on TACC and record the outcome in [docs/tacc-notes.md](../tacc-notes.md).
- The execution boundary is settled in [ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md); implement the restricted runner and wire interrupt based confirmation for user supplied code.
- Update the directory mapping in [AGENTS.md](../../AGENTS.md) when the orchestrator package lands.

## Alternatives considered

**Hand-written asyncio state machine (the previous decision).** For: full control, no new dependencies, and budgets enforced in one place. Against: checkpointing, resume, streaming events, and human in the loop would all be rebuilt in project code, and the lead chose LangGraph; replaced by this record.

**LangChain agents or LangGraph prebuilt ReAct graphs.** For: a faster first prototype with tool calling built in. Against: implicit control flow and hidden budgets, which the project rejected for auditability; the project uses LangGraph explicitly instead.

**LlamaIndex Workflows.** For: comparable event-driven orchestration with a smaller dependency group. Against: the team selected LangGraph and the Langfuse integration path is documented for it.

**LangGraph Platform or LangGraph Server.** For: managed hosting, queues, and deployment. Against: the platform has no Node runtime or managed service for student projects, and one FastAPI process is enough at course scale.

## References

- LangGraph 1.2.18 inspected on 2026-10-29: https://pypi.org/project/langgraph
- LangGraph documentation: https://langchain-ai.github.io/langgraph/
- Langfuse LangGraph integration guide: https://langfuse.com/integrations/frameworks/langgraph
- Streaming contract: [ADR-0003](0003-react-spa-with-ai-elements.md)
- Local tracing: [ADR-0007](0007-langfuse-for-local-model-call-tracing.md)
- Environment strategy: [ADR-0001](0001-pinned-python-environment-without-docker.md)
- Previous orchestration choice: [../tech-selection.md](../tech-selection.md)
