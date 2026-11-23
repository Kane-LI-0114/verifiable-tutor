# Product differentiation: what a general web LLM cannot do

This page lists the capabilities of the verifiable tutor that a general web LLM
chat (for example Gemini, Doubao, or Qwen) cannot reproduce. It is the
reference list for the product differentiation argument in the evaluation.

| Capability | Description |
|---|---|
| Course-specific retrieval (RAG) | The tutor answers from the pre-vectorized course corpus (382 chunks across 13 lectures, tutorials, and assignments). A general web LLM has no access to this course's notes, assignments, or lectures beyond its training data and general web search. |
| Sentence-level citations | Every claim in an answer carries a `[ref_N]` marker that resolves to a specific corpus page or chunk. A general web LLM does not emit verifiable, sentence-level citations into course material. |
| Citation verification (span verifier) | The tutor can check whether a cited span actually supports the claim and emit a verdict. A general web LLM has no citation-verification step. |
| Knowledge-point progress (Mastery) | The tutor tracks, per topic, which knowledge points a student has covered and mastered; the progress only grows. A general web LLM is stateless and does not remember what a student has learned. |
| Assignment deadline guard (Guardrail) | The tutor knows each assignment's deadline and refuses a complete homework solution before it. A general web LLM answers directly, which can breach academic integrity. |
| Structured practice loop | The tutor generates questions tagged with knowledge points, grades objective questions deterministically, and updates mastery from the result. A general web LLM is chat only; it has no practice, grading, and progress loop. |
| Persisted, replayable sessions | Every practice run and chat is stored as a conversation that can be browsed and replayed from the sidebar. A general web LLM keeps only a simple chat history with no structured query. |
| Closed-domain hallucination guard | The tutor answers from the course material and does not invent content the course does not contain. A general web LLM can hallucinate facts or citations. |
| Explicit knowledge-point denominator | Each topic has a fixed knowledge-point list (8/5/4/3/4), so coverage can be quantified. A general web LLM has no structured knowledge list. |
