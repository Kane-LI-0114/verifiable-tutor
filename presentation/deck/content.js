const slides = [
  {
    section: "CSIT6000V / FINAL PRESENTATION / FALL 2026",
    title: "Verifiable Tutor",
    notes: "0:15. A tutor that can show its work. Every answer names the page it came from, and every practice question carries a reference answer.",
  },
  {
    section: "01 / PROBLEM & GOAL",
    title: "A study loop students can trust.",
    notes: "0:45. The user is a CSIT6000V student. The job is to keep up with dense material, practise at assignment scale, and know what help is allowed. The pain is that a fluent answer is not a checkable answer. We chose the task-oriented direction: measure the study loop against hosted assistants, not system efficiency.",
  },
  {
    section: "02 / SYSTEM",
    title: "One local product. One batch backend on TACC.",
    notes: "0:45. The product runs on the laptop: React SPA, FastAPI, LangGraph, SQLite and local files. TACC is a required model-serving backend, but only through submitted batch jobs: OCR, index, and the Qwen knowledge-base job. No inbound service. The bottom strip is the one-turn flow.",
  },
  {
    section: "03 / DATA",
    title: "The data model makes the evidence chain durable.",
    notes: "0:30. All durable state is one local SQLite database: identity, conversations and the work chain, and the knowledge store. message_sources is the bridge from an answer to a document page; citations is the verified layer we are still wiring.",
  },
  {
    section: "04 / STACK",
    title: "A small stack with one job per layer.",
    notes: "0:25. The UI is a React SPA served by FastAPI; the agent is a typed LangGraph loop; retrieval is SQLite FTS5 plus BGE-M3; and batch model jobs run on TACC. Versions are pinned in package.json and pyproject.toml.",
  },
  {
    section: "05 / FUNCTIONS / AGENT",
    title: "A typed loop, not a prompt.",
    notes: "0:40. Perception is the message, history, document context, and tool results. Planning is model-driven inside the agent node, constrained by a closed tool set. Execution validates arguments and streams results. Reflection is tool-mediated: verify_span, same-model retries, abstain when evidence is missing.",
  },
  {
    section: "06 / DEMO / AGENT",
    title: "Watch the loop work.",
    notes: "0:30. This is a real turn: five retrieval calls, two page reads, and four span checks. verify_span carries the doc id, page number, and exact quote. The output is span verified. Every call is persisted in the work chain and can be replayed from JSONL.",
  },
  {
    section: "07 / FUNCTIONS / RAG OFFLINE",
    title: "Build the evidence base on TACC.",
    notes: "0:35. Offline, the course PDFs are parsed by a TACC OCR job, chunked page-first, embedded with BGE-M3 on TACC, and imported into the local SQLite store. The index never runs at request time. 16 documents, 593 pages, 612 chunks and vectors.",
  },
  {
    section: "08 / FUNCTIONS / RAG ONLINE",
    title: "Retrieve pages, then let the model read.",
    notes: "0:35. Online, the model writes the tool query. FTS5 BM25 and a local BGE-M3 query embedding each return 30 candidates. RRF fuses them, and the tool returns page-anchored text with a marker. The model reads the page and checks the quote before answering.",
  },
  {
    section: "09 / DEMO / RAG",
    title: "Every paragraph names its source.",
    notes: "0:30. This is the source pane for one answer: 14 retrieved course pages in marker order. A marker opens the exact page. A source is retrieved evidence, not yet a verified citation; the verifier is the next layer.",
  },
  {
    section: "10 / FUNCTIONS / KNOWLEDGE",
    title: "A conversation that lives beside the file.",
    notes: "0:30. Every turn carries doc_id and page_no. The system note names the file and page but does not inject the page text; the model must call read_course_page. A citation target is a URL to that exact page, and the conversation belongs to the file.",
  },
  {
    section: "11 / DEMO / KNOWLEDGE",
    title: "From a marker to the exact page.",
    notes: "0:30. The open file is Lecture 2, page 9. The answer cites page 9, page 10, page 11 and a cross-document page. Clicking the page-10 marker moves the PDF to page 10 while the chat stays in place.",
  },
  {
    section: "12 / VERIFIER",
    title: "A source is not a citation until the span passes.",
    notes: "0:30. The verifier normalizes whitespace and case, requires the quoted span to occur on the cited page, allows one repair round, and otherwise abstains. Pass becomes a citation; fail goes back to repair or abstention. Persisting the verified layer is the next step.",
  },
  {
    section: "13 / FUNCTIONS / PRACTICE & POLICY",
    title: "Practice and integrity.",
    notes: "0:30. Practice and self-test share one question record: five types, a reference answer, scoring points, and course citations. Choice questions are graded deterministically; open and code answers are model-graded. The disclosure gate is code, with five states from a dated registry.",
  },
  {
    section: "14 / DEMO / PRACTICE & POLICY",
    title: "Practice, then check.",
    notes: "0:25. The student chooses a topic and type; the question comes from the course with a page marker. Before the deadline, a complete Assignment 3 solution is blocked and the refusal points to concepts, a similar example, or a hint.",
  },
  {
    section: "15 / EVALUATION",
    title: "We win on coverage and quote integrity. We tie on grading.",
    notes: "0:35. On ten practice questions we match the best control on groundedness, lead on knowledge-point coverage, and tie on grading. In the 15-question citation study we invent no quotes and no false negatives, and page numbers are programmatic. Ties are reported as ties.",
  },
  {
    section: "16 / FAILURE & LIMITS",
    title: "Tutorials are the hard slice.",
    notes: "0:35. Tutorial questions retrieve worse than concept, mechanism or assignment questions. The likely cause is that tutorial pages bundle several sub-tasks into one page. Dual-granularity chunking raised hit@5 but not significantly, at 2.7 times the index cost, so we kept the page-first rule and logged it.",
  },
  {
    section: "17 / CONCLUSION",
    title: "Verifiability is a system property.",
    notes: "0:30. The page is the retrieval unit, the policy is code, and the evaluation separates grounding from grading. The student loop is end-to-end. The operator console, verifier persistence, TACC execution, and multi-course support are the next surfaces.",
  },
  {
    section: "APPENDIX / A1",
    title: "One question, end to end.",
    notes: "Appendix. The sequence from student to answer: SPA, API, gate, LangGraph, typed tools, verifier, model, store, and SSE. Solid is shipped; dashed is planned.",
  },
  {
    section: "APPENDIX / A2",
    title: "Evaluation method and TACC evidence.",
    notes: "Appendix. Ten practice questions and fifteen citation questions against three hosted assistants. The Qwen knowledge-base job 28067 measured a 434 second cold start, 43.9 second build, and 8 of 8 valid records.",
  },
];

module.exports = { slides };
