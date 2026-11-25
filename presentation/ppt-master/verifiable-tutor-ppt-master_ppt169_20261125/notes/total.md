# 01_cover

A tutor that can show its work. Every answer names the page it came from, and every practice item carries a reference. The screenshot behind the title is a real source pane, not a mockup. Three numbers preview the agent turn: five retrieval calls, two page reads, and four span checks.

---

# 02_problem

The user is one CSIT6000V student with a dense course load. The study loop has three trust gaps: finding the right page, practising at assignment scale, and knowing what help is allowed before a deadline. A fluent answer does not close any of them. We chose the course brief's task-oriented direction, so the comparison is the study loop against hosted assistants, not system throughput.

---

# 03_architecture

The product runs on the laptop. A React SPA talks to one FastAPI process over SSE. Inside that process are the LangGraph loop, the policy gate, retrieval and the span verifier, practice and grading, and one SQLite store. TACC is a required backend, but only through submitted batch jobs for OCR, indexing, and the Qwen knowledge-base run. There is no inbound service, so the diagram keeps the batch rail separate.

---

# 04_database

All durable state is one local SQLite file: seventeen application tables plus FTS5. The table that matters for this talk is message_sources, the bridge from an answer to a document page. The knowledge cluster holds the corpus and the index state. The citations table exists but is empty; it is the verified layer we are still wiring, and the deck labels it as next.

---

# 05_stack

Each layer has one job. The interface is a React SPA built with Vite and Tailwind. FastAPI serves the API and the stream. The agent is a typed LangGraph loop. Retrieval is SQLite FTS5 plus BGE-M3, with the span verifier beside it. TACC runs PaddleOCR, the index job, and Qwen. External model and mail APIs are edges, not part of the local core.

---

# 06_agent

This is a typed loop, not a prompt. Perception receives the message, history, document context, and tool results. Planning happens inside the agent node under a closed tool set. Execution validates arguments and streams results. Reflection is tool-mediated: verify_span, bounded retries, and abstention when the evidence is missing. Every step is persisted, so a turn can be replayed.

---

# 07_agent_demo

Here is one real turn. Five retrieval calls, two page reads, and four verify_span calls. The expanded call carries the document id, page nine, and the exact quote; the output is span verified. That is the loop doing evidence work, not just generating prose. The work chain and trace are stored, so this is replayable rather than a one-off recording.

---

# 08_rag_offline

The evidence base is built offline on TACC. PaddleOCR parses the course PDFs, the chunker keeps pages first with a 450-token budget, and BGE-M3 writes the vectors. The import lands in local SQLite with float32 vectors. The result is sixteen documents, 593 pages, and 612 chunks and vectors. The index never runs at request time.

---

# 09_rag_online

Online, the model writes the tool query. FTS5 BM25 and a local BGE-M3 embedding each return thirty candidates. RRF fuses the two lists, the model reads the page, and verify_span checks the quote before the answer. The measured retrieval is nDCG@5 0.849 and hit@5 0.882 at 937 tokens for five results. Pages, not loose text, are the unit.

---

# 10_rag_demo

This is the source pane for one answer: fourteen course pages in marker order. A marker opens the exact page. The important distinction is that a source is retrieved evidence, not yet a citation. The verifier is a separate layer; the marker alone does not prove that the quoted span occurs on the page.

---

# 11_knowledge

Every knowledge-chat turn carries a document id and a page number, and the conversation belongs to the file. The system note names the file and page, but it does not inject the page text. The model still has to call read_course_page. That keeps the file pane and the chat on one route without turning the note into hidden evidence.

---

# 12_knowledge_demo

The open file is Lecture 2, page nine. The answer cites page nine and page ten. Clicking the page-ten marker moves the PDF to page ten while the chat stays in place. The target is a URL to that exact page. This is the interaction that makes a citation usable for study rather than just decorative.

---

# 13_verifier

A source becomes a citation only after the span check. The verifier normalizes whitespace and case, locates the quoted span on the cited page, allows one bounded repair, and otherwise abstains. Pass becomes a citation; fail goes back to repair or no answer. The part still missing is persistence: the citations table is empty, and we say so.

---

# 14_practice_policy

Practice and permission are different guardrails. Practice has five question types, a reference answer, scoring points, and page markers; choice questions are graded deterministically, while open and code answers use the model. The disclosure gate has five states from a dated registry and is enforced server-side. Before the deadline, a complete Assignment 3 solution is refused.

---

# 15_practice_demo

On the left is a real practice item: a FlashAttention single-choice question with a page marker and two points. On the right is the policy refusal for a complete Assignment 3 solution before 2026-11-29. It offers concepts, a similar example, or a hint. Same user, same course, two different guardrails doing their jobs.

---

# 16_evaluation

On ten practice questions we tie the best baseline on groundedness at ten out of ten, lead on knowledge-point coverage at five out of five versus three out of five, and tie on grading at ten out of ten. In the fifteen-question citation study we invent no quotes and report no false not-in-PDF cases. Page numbers are programmatic. Ties are reported as ties, not folded into a win.

---

# 17_failure

Tutorials are the hard slice. Their nDCG@5 is 0.617, below concept, mechanism, and assignment questions. The likely cause is that tutorial pages bundle several sub-tasks. Dual-granularity chunking raised hit@5 from 0.882 to 0.941, but the nDCG confidence interval crosses zero and the index cost is 2.7 times higher. We kept the page-first rule and logged the result.

---

# 18_conclusion

Three properties hold the system together. The page is the retrieval unit, so answers, citations, and the file view share one coordinate. Policy is code, not a prompt. Evaluation separates grounding from grading, which is why the ties stay visible. The next surfaces are an operator console for instructor and TA use, citation persistence, TACC execution, and multi-course support. Questions are welcome.

---

# 19_appendix_a1

This is the full path for one question. The SPA sends the task, FastAPI owns the origin, the policy gate allows or refuses, LangGraph runs the loop, and the typed tools read and verify. The result goes through the model adapter into SQLite and JSONL, then back over SSE. The citation store is dashed because persistence is still planned, not shipped.

---

# 20_appendix_a2

The evaluation uses ten practice questions and fifteen citation questions against Doubao, Gemini, and Qwen. The retrieval study uses fifty-one questions and reports nDCG@5 and hit@5. The TACC receipt is job 28067: 434 seconds of cold start, 43.9 seconds for the eight-chunk build, and eight of eight valid records. One job is a receipt, not an average.
