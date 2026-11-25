const SPEAKER_NOTES = [
  {
    id: 'cover', title: 'Verifiable Tutor', section: 'CSIT6000V / FINAL PRESENTATION / FALL 2026', minutes: 0.25,
    purpose: 'Open with the promise: a tutor that can show its work.',
    talk: [
      'A tutor that can show its work.',
      'Every answer names the page it came from.',
      'Every practice question carries a reference answer.'
    ],
    transition: 'Name the problem before showing the product.',
    cue: 'Check that the audience screen is synced before starting.'
  },
  {
    id: 'problem-goal', title: 'A study loop students can trust.', section: '01 / PROBLEM & GOAL', minutes: 0.75,
    purpose: 'Frame the student job and why fluent answers fail it.',
    talk: [
      'The user is a CSIT6000V student keeping up with dense material.',
      'The job is to practise at assignment scale and know what help is allowed.',
      'The pain is simple: a fluent answer is not a checkable answer.',
      'We chose the task-oriented direction and measure the study loop against hosted assistants.'
    ],
    transition: 'Show the system that closes that loop.',
    advance: 'Move on after "checkable answer".'
  },
  {
    id: 'system', title: 'One local product. One batch backend on TACC.', section: '02 / SYSTEM', minutes: 0.75,
    purpose: 'Establish the product boundary and the TACC boundary.',
    talk: [
      'The product runs on the laptop: React SPA, FastAPI, LangGraph, SQLite and local files.',
      'TACC is a required model-serving backend, reached only through submitted batch jobs.',
      'OCR, index and the Qwen knowledge-base job run there; there is no inbound service.',
      'The bottom strip is the one-turn flow.'
    ],
    transition: 'Durable evidence needs a schema, so start with the data model.'
  },
  {
    id: 'data', title: 'The data model makes the evidence chain durable.', section: '03 / DATA', minutes: 0.5,
    purpose: 'Show where the evidence chain lives and where it stops.',
    talk: [
      'All durable state is one local SQLite database.',
      'Identity, conversations and the work chain, and the knowledge store are the clusters.',
      'message_sources is the bridge from an answer to a document page.',
      'citations is the verified layer we are still wiring.'
    ],
    transition: 'The schema is small, and so is the stack around it.'
  },
  {
    id: 'stack', title: 'A small stack with one job per layer.', section: '04 / STACK', minutes: 0.4167,
    purpose: 'Give one line per layer without turning the deck into a dependency list.',
    talk: [
      'The UI is a React SPA served by FastAPI.',
      'The agent is a typed LangGraph loop.',
      'Retrieval is SQLite FTS5 plus BGE-M3.',
      'Batch model jobs run on TACC; versions are pinned in package.json and pyproject.toml.'
    ],
    transition: 'Now open the agent loop itself.'
  },
  {
    id: 'agent', title: 'A typed loop, not a prompt.', section: '05 / FUNCTIONS / AGENT', minutes: 0.6667,
    purpose: 'Explain perception, planning, execution and reflection as one closed loop.',
    talk: [
      'Perception is the message, history, document context and tool results.',
      'Planning is model-driven inside the agent node, constrained by a closed tool set.',
      'Execution validates arguments and streams bounded results.',
      'Reflection is tool-mediated: verify_span, same-model retries, abstain when evidence is missing.'
    ],
    transition: 'Here is that loop on a real turn.'
  },
  {
    id: 'agent-demo', title: 'Watch the loop work.', section: '06 / DEMO / AGENT', minutes: 0.5,
    purpose: 'Make the loop concrete with one persisted turn.',
    talk: [
      'This is a real turn: five retrieval calls, two page reads and four span checks.',
      'verify_span carries the doc id, page number and exact quote.',
      'The output is span verified.',
      'Every call is persisted in the work chain and can be replayed from JSONL.'
    ],
    transition: 'The loop reads an evidence base that is built offline.'
  },
  {
    id: 'rag-offline', title: 'Build the evidence base on TACC.', section: '07 / FUNCTIONS / RAG OFFLINE', minutes: 0.5833,
    purpose: 'Show the offline pipeline and the corpus scale.',
    talk: [
      'Offline, course PDFs are parsed by a TACC OCR job and chunked page-first.',
      'BGE-M3 embeds the chunks on TACC and the vectors are imported into local SQLite.',
      'The index never runs at request time.',
      '16 documents, 593 pages, 612 chunks and vectors.'
    ],
    transition: 'At request time the corpus is queried with two retrieval arms.'
  },
  {
    id: 'rag-online', title: 'Retrieve pages, then let the model read.', section: '08 / FUNCTIONS / RAG ONLINE', minutes: 0.5833,
    purpose: 'Explain hybrid retrieval and the page-anchored tool boundary.',
    talk: [
      'The model writes the tool query.',
      'FTS5 BM25 and a local BGE-M3 query embedding each return 30 candidates.',
      'RRF fuses them and the tool returns page-anchored text with a marker.',
      'The model reads the page and checks the quote before answering.'
    ],
    transition: 'The source pane is what the student sees from that pipeline.'
  },
  {
    id: 'rag-demo', title: 'Every paragraph names its source.', section: '09 / DEMO / RAG', minutes: 0.5,
    purpose: 'Show marker-to-page evidence and hold the source versus citation line.',
    talk: [
      'This is the source pane for one answer: 14 retrieved course pages in marker order.',
      'A marker opens the exact page.',
      'A source is retrieved evidence, not yet a verified citation.',
      'The verifier is the next layer.'
    ],
    transition: 'The same page anchoring powers the knowledge-base chat.'
  },
  {
    id: 'knowledge', title: 'A conversation that lives beside the file.', section: '10 / FUNCTIONS / KNOWLEDGE', minutes: 0.5,
    purpose: 'Show document context as context, not as a pre-filled prompt.',
    talk: [
      'Every turn carries doc_id and page_no.',
      'The system note names the file and page but does not inject the page text.',
      'The model must call read_course_page.',
      'A citation target is a URL to that exact page, and the conversation belongs to the file.'
    ],
    transition: 'One click shows the page jump.'
  },
  {
    id: 'knowledge-demo', title: 'From a marker to the exact page.', section: '11 / DEMO / KNOWLEDGE', minutes: 0.5,
    purpose: 'Demonstrate before and after on page 9 and page 10.',
    talk: [
      'The open file is Lecture 2, page 9.',
      'The answer cites page 9, page 10, page 11 and a cross-document page.',
      'Clicking the page-10 marker moves the PDF while the chat stays in place.'
    ],
    transition: 'A page jump is not verification, so meet the verifier.'
  },
  {
    id: 'verifier', title: 'A source is not a citation until the span passes.', section: '12 / VERIFIER', minutes: 0.5,
    purpose: 'State the verifier contract and the shipped gap.',
    talk: [
      'The verifier normalizes whitespace and case.',
      'It requires the quoted span to occur on the cited page.',
      'It allows one repair round and otherwise abstains.',
      'Pass becomes a citation; persisting the verified layer is the next step; the implementation is Yoga’s.',
      'citations is still empty today.'
    ],
    transition: 'The same discipline covers practice and disclosure.'
  },
  {
    id: 'practice-policy', title: 'Practice and integrity.', section: '13 / FUNCTIONS / PRACTICE & POLICY', minutes: 0.5,
    purpose: 'Unify practice records and the disclosure gate.',
    talk: [
      'Practice and self-test share one question record: five types, a reference answer, scoring points and course citations.',
      'Choice questions are graded deterministically; open and code answers are model-graded.',
      'The disclosure gate is code with five states from a dated registry.'
    ],
    transition: 'Two screenshots show both halves.'
  },
  {
    id: 'practice-demo', title: 'Practice, then check.', section: '14 / DEMO / PRACTICE & POLICY', minutes: 0.4167,
    purpose: 'Show the generated question and the policy refusal.',
    talk: [
      'The student chooses a topic and type.',
      'The question comes from the course with a page marker.',
      'Before the deadline a complete Assignment 3 solution is blocked.',
      'The refusal points to concepts, a similar example or a hint.'
    ],
    transition: 'Now measure the result instead of asserting it.'
  },
  {
    id: 'evaluation', title: 'We win on coverage. We tie on grading.', section: '15 / EVALUATION', minutes: 0.5833,
    purpose: 'Report the evaluation honestly, ties included.',
    talk: [
      'On ten practice questions we match the best control on groundedness.',
      'We lead on knowledge-point coverage: 5/5 against 3/5.',
      'We invent no quotes and make no false negatives in the citation study.',
      'Grading is a tie across all four systems, and we report it as a tie.'
    ],
    transition: 'The weak slice deserves its own page.'
  },
  {
    id: 'failure-limits', title: 'Tutorials are the hard slice.', section: '16 / FAILURE & LIMITS', minutes: 0.5833,
    purpose: 'Name the failure, the lesson and the four limits.',
    talk: [
      'Tutorial questions retrieve worse than concept, mechanism or assignment questions.',
      'The likely cause is that tutorial pages bundle several sub-tasks into one page.',
      'Dual-granularity chunking raised hit@5 but not significantly, at 2.7 times the index cost.',
      'We kept the page-first rule and logged it; the instructor/TA console is still partial.'
    ],
    transition: 'Close on the property that ties the system together.'
  },
  {
    id: 'conclusion', title: 'Verifiability is a system property.', section: '17 / CONCLUSION', minutes: 0.5,
    purpose: 'Close the loop and name the next surfaces.',
    talk: [
      'The page is the retrieval unit.',
      'The policy is code.',
      'The evaluation separates grounding from grading.',
      'The student loop is end-to-end; the instructor/TA console, verifier persistence, TACC execution and multi-course support are next.'
    ],
    transition: 'Stop for questions and point at the repository QR code.',
    cue: 'Pause for two seconds, then invite questions.'
  },
  {
    id: 'appendix-a1', title: 'One question, end to end.', section: 'APPENDIX / A1', minutes: 0.2,
    purpose: 'Keep the full sequence available for questions.',
    talk: [
      'The sequence from student to answer: SPA, API, gate, LangGraph, typed tools, verifier, model, store and SSE.',
      'Solid is shipped; outlined is planned or partial.',
      'The verifier is outlined because persistence is not wired yet.'
    ],
    transition: 'Appendix A2 holds the method and TACC evidence.'
  },
  {
    id: 'appendix-a2', title: 'Evaluation method and TACC evidence.', section: 'APPENDIX / A2', minutes: 0.2,
    purpose: 'Keep evaluation method and TACC measurements available for questions.',
    talk: [
      'Ten practice questions and fifteen citation questions against three hosted assistants.',
      'The Qwen knowledge-base job 28067 measured a 434 second cold start.',
      'The eight-chunk build took 43.9 seconds and returned 8 of 8 valid records.'
    ],
    transition: 'End of deck.'
  }
];
window.__SPEAKER_NOTES__ = SPEAKER_NOTES;
