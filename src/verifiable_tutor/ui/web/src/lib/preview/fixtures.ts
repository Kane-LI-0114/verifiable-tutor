import type {
  ChatMessage,
  Citation,
  CitationSource,
  Conversation,
  ConversationTurn,
  DeadlineRegistry,
  GradingResult,
  KnowledgeBuild,
  KnowledgeCard,
  Me,
  PracticeQuestion,
} from "@/lib/types";

export const PREVIEW_STUDENT: Me = {
  id: "6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8",
  email: "student@ust.hk",
  role: "student",
  created_at: "2026-10-20T08:00:00+00:00",
};

export const PREVIEW_INSTRUCTOR: Me = {
  id: "0a1b2c3d4e5f60718293a4b5c6d7e8f9",
  email: "ta@ust.hk",
  role: "instructor",
  created_at: "2026-10-01T08:00:00+00:00",
};

export const PREVIEW_SESSIONS: Conversation[] = [
  {
    id: "6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8",
    title: "How does MPI_Allreduce work?",
    created_at: "2026-11-03T09:12:00+00:00",
    updated_at: "2026-11-03T09:13:20+00:00",
    message_count: 2,
  },
  {
    id: "a1b2c3d4e5f60718293a4b5c6d7e8f90",
    title: "Attention softmax stability",
    created_at: "2026-11-02T14:04:00+00:00",
    updated_at: "2026-11-02T14:06:10+00:00",
    message_count: 2,
  },
  {
    id: "b2c3d4e5f60718293a4b5c6d7e8f9012",
    title: "Assignment 2 kernel layout",
    created_at: "2026-10-31T20:30:00+00:00",
    updated_at: "2026-10-31T20:35:00+00:00",
    message_count: 2,
  },
];

const CITATION_ALLREDUCE: Citation = {
  doc_id: "ACS_lecture_2_2026F",
  page_no: 12,
  quote: "MPI_Allreduce combines values from all ranks and distributes the result to all ranks.",
  bbox_norm: [0.08, 0.22, 0.9, 0.3],
};

const CITATION_COURSE_PROJECT: Citation = {
  doc_id: "course_project",
  page_no: 1,
  quote: "Building an End-to-End Agent System",
  bbox_norm: [0.12, 0.18, 0.86, 0.26],
};

const CITATION_TACC_TUTORIAL: Citation = {
  doc_id: "TACC_Toturial",
  page_no: 4,
  quote: "Submit the job with tcloud submit and record the Job ID.",
  bbox_norm: [0.1, 0.42, 0.88, 0.5],
};

export const PREVIEW_CITATIONS: Citation[] = [
  CITATION_ALLREDUCE,
  CITATION_COURSE_PROJECT,
  CITATION_TACC_TUTORIAL,
];

export const PREVIEW_SOURCES: CitationSource[] = [
  {
    marker: 1,
    kind: "course",
    title: "Lecture 2: Collectives",
    summary:
      "MPI_Allreduce combines values from all ranks and distributes the result to all ranks.",
    doc_id: "ACS_lecture_2_2026F",
    page_no: 12,
    url: null,
  },
  {
    marker: 2,
    kind: "course",
    title: "Reduction and broadcast",
    summary:
      "MPI_Reduce leaves the result on the root, while MPI_Allreduce broadcasts it.",
    doc_id: "ACS_lecture_2_2026F",
    page_no: 13,
    url: null,
  },
  {
    marker: 3,
    kind: "course",
    title: "TACC Tutorial",
    summary: "Submit the job with tcloud submit and record the Job ID.",
    doc_id: "TACC_Toturial",
    page_no: 4,
    url: null,
  },
  {
    marker: 4,
    kind: "web",
    title: "DeepSeek API documentation",
    summary: "Search and fetch API reference for external sources.",
    doc_id: null,
    page_no: null,
    url: "https://api-docs.deepseek.com/guides/search",
  },
];


const QUESTION: ChatMessage = {
  id: "message-user-1",
  sequence: 1,
  role: "user",
  content: "How does MPI_Allreduce work, and when should I use it in the GEMM assignment?",
  provider: null,
  tier: null,
  created_at: "2026-11-03T09:12:04+00:00",
  reasoning: null,
  model: null,
  thinking: null,
  work_steps: [],
  citations: [],
  sources: [],
  tool_calls: [],
};

const ANSWER: ChatMessage = {
  id: "message-assistant-1",
  sequence: 2,
  role: "assistant",
  content: [
    "`MPI_Allreduce` is a collective that reduces one value per rank and leaves the result on **every** rank. It is the reduction counterpart of `MPI_Reduce`, which leaves the result only on the root. [ref_1]",
    "",
    "For a row of the output matrix, you can sum the partial products across ranks:",
    "",
    "$$C_{ij} = \\sum_{k} A_{ik} B_{kj}$$",
    "",
    "The call is:",
    "",
    "```c",
    "MPI_Allreduce(local, global, count, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);",
    "```",
    "",
    "Use it when every rank needs the reduced block, for example before writing the output tile. If only rank 0 writes the result, `MPI_Reduce` is cheaper. [ref_2]",
    "",
    "Submit the assignment job with `tcloud submit` and keep the returned Job ID. The API reference is external material. [ref_3] [ref_4]",
  ].join("\n"),
  provider: "deepseek",
  tier: "flash",
  created_at: "2026-11-03T09:13:20+00:00",
  reasoning: null,
  model: null,
  thinking: null,
  work_steps: [],
  citations: [],
  sources: [],
  tool_calls: [],
};

export const PREVIEW_TURNS: ConversationTurn[] = [
  { message: QUESTION },
  {
    message: ANSWER,
    meta: {
      policy_state: "active",
      reasoning:
        "The question asks about a collective operation and its use in the assignment. The assignment is active, so I can explain the operation and the call, but I should not produce the missing kernel implementation.",
      citations: PREVIEW_CITATIONS,
      sources: PREVIEW_SOURCES,
      tool_calls: [
        {
          name: "course_search",
          command: ["course_search", "--query", "MPI_Allreduce", "--top-k", "5"],
          exit_code: 0,
          output:
            "ACS_lecture_2_2026F p.12 (0.84)\nACS_lecture_2_2026F p.13 (0.71)\ntutorial/TACC_Toturial p.4 (0.42)",
          status: "done",
        },
        {
          name: "span_verify",
          command: ["span_verify", "--doc", "ACS_lecture_2_2026F", "--page", "12"],
          exit_code: 0,
          output: "2 of 2 quoted passages found on the page.",
          status: "done",
        },
      ],
      events: [
        {
          kind: "reasoning",
          step_id: "retrieve",
          reasoning:
            "The question asks about a collective operation and its use in the assignment. The assignment is active, so I can explain the operation and the call, but I should not produce the missing kernel implementation.",
        },
        {
          kind: "tool_call",
          step_id: "retrieve",
          tool_call: {
            name: "course_search",
            command: ["course_search", "--query", "MPI_Allreduce", "--top-k", "5"],
            exit_code: 0,
            output:
              "ACS_lecture_2_2026F p.12 (0.84)\nACS_lecture_2_2026F p.13 (0.71)\ntutorial/TACC_Toturial p.4 (0.42)",
            status: "done",
          },
        },
        {
          kind: "tool_call",
          step_id: "verify",
          tool_call: {
            name: "span_verify",
            command: [
              "span_verify",
              "--doc",
              "ACS_lecture_2_2026F",
              "--page",
              "12",
            ],
            exit_code: 0,
            output: "2 of 2 quoted passages found on the page.",
            status: "done",
          },
        },
      ],
      work_steps: [
        { id: "understand", step: "understand", status: "done", duration_ms: 320 },
        {
          id: "retrieve",
          step: "retrieve",
          status: "done",
          duration_ms: 1180,
          detail: "Hybrid retrieval returned 5 pages, 3 cited.",
        },
        {
          id: "verify",
          step: "verify",
          status: "done",
          duration_ms: 140,
          detail: "All quoted passages found on their pages.",
        },
        {
          id: "decide",
          step: "decide",
          status: "done",
          duration_ms: 12,
          policy: "active",
          rule_id: "active.explain-current-topic",
        },
        { id: "generate", step: "generate", status: "done", duration_ms: 2400 },
        { id: "cite", step: "cite", status: "done", duration_ms: 64 },
      ],
    },
  },
];

const CITATION_SOFTMAX: Citation = {
  doc_id: "ACS_lecture_3_2026F",
  page_no: 9,
  quote:
    "Subtracting the row maximum before the exponential keeps the computation numerically stable.",
  bbox_norm: [0.1, 0.34, 0.88, 0.42],
};

const CITATION_KERNEL: Citation = {
  doc_id: "ACS_lecture_4_2026F",
  page_no: 5,
  quote:
    "Tile the score matrix so each warp reduces one row without leaving shared memory.",
  bbox_norm: [0.12, 0.3, 0.9, 0.38],
};

const QUESTION_ATTENTION: ChatMessage = {
  id: "message-user-attention-1",
  sequence: 1,
  role: "user",
  content: "Why does the softmax in attention subtract the row maximum?",
  provider: null,
  tier: null,
  created_at: "2026-11-02T14:04:02+00:00",
  reasoning: null,
  model: null,
  thinking: null,
  work_steps: [],
  citations: [],
  sources: [],
  tool_calls: [],
};

const ANSWER_ATTENTION: ChatMessage = {
  id: "message-assistant-attention-1",
  sequence: 2,
  role: "assistant",
  content: [
    "Attention scores can be large, and `exp` overflows once a score passes about 709. Subtracting the row maximum shifts every score by the same constant, so the largest exponent becomes `exp(0) = 1` and the sum stays finite.",
    "",
    "$$p_{ij} = \\frac{\\exp(s_{ij} - m_i)}{\\sum_k \\exp(s_{ik} - m_i)}$$",
    "",
    "With $$m_i = \\max_k s_{ik}$$ every term is at most one, so the normalizer cannot overflow. The result matches the exact softmax because $$e^{s_{ij} - m_i} = e^{s_{ij}} / e^{m_i}$$ cancels between the numerator and the denominator.",
    "",
    "The assignment asks for this per-row maximum in every attention block, in fp32 and in the reference kernel.",
  ].join("\n"),
  provider: "deepseek",
  tier: "flash",
  created_at: "2026-11-02T14:06:10+00:00",
  reasoning: null,
  model: null,
  thinking: null,
  work_steps: [],
  citations: [],
  sources: [],
  tool_calls: [],
};

const QUESTION_KERNEL: ChatMessage = {
  id: "message-user-kernel-1",
  sequence: 1,
  role: "user",
  content: "How should I lay out the CUDA kernel for the attention assignment?",
  provider: null,
  tier: null,
  created_at: "2026-10-31T20:30:04+00:00",
  reasoning: null,
  model: null,
  thinking: null,
  work_steps: [],
  citations: [],
  sources: [],
  tool_calls: [],
};

const ANSWER_KERNEL: ChatMessage = {
  id: "message-assistant-kernel-1",
  sequence: 2,
  role: "assistant",
  content: [
    "Start from the tile the assignment describes: one block owns a tile of the score matrix, and each warp owns one row of that tile.",
    "",
    "1. Load the query tile and the key tile into shared memory once per block.",
    "2. Each warp computes the dot products for its row and keeps the row maximum in registers.",
    "3. Apply the exponential after subtracting the row maximum, then accumulate the row sum.",
    "4. Write the normalized tile back to global memory.",
    "",
    "The assignment scores the layout and the stable softmax separately, so keep the row reduction inside the warp:",
    "",
    "```cuda",
    "__shared__ float tile_q[TILE][HEAD_DIM];",
    "__shared__ float tile_k[TILE][HEAD_DIM];",
    "float row_max = warp_reduce_max(score);",
    "```",
  ].join("\n"),
  provider: "deepseek",
  tier: "flash",
  created_at: "2026-10-31T20:35:00+00:00",
  reasoning: null,
  model: null,
  thinking: null,
  work_steps: [],
  citations: [],
  sources: [],
  tool_calls: [],
};

const ATTENTION_TURNS: ConversationTurn[] = [
  { message: QUESTION_ATTENTION },
  {
    message: ANSWER_ATTENTION,
    meta: {
      policy_state: "active",
      reasoning:
        "The question asks about numerical stability rather than for the assignment kernel. The assignment is active, so I can explain the stabilization trick and leave the kernel code base to the student.",
      citations: [CITATION_SOFTMAX],
      sources: [PREVIEW_SOURCES[0]],
      tool_calls: [
        {
          name: "course_search",
          command: ["course_search", "--query", "softmax row maximum", "--top-k", "5"],
          exit_code: 0,
          output:
            "ACS_lecture_3_2026F p.9 (0.91)\nACS_lecture_3_2026F p.10 (0.77)\nACS_lecture_4_2026F p.5 (0.35)",
          status: "done",
        },
        {
          name: "span_verify",
          command: ["span_verify", "--doc", "ACS_lecture_3_2026F", "--page", "9"],
          exit_code: 0,
          output: "1 of 1 quoted passage found on the page.",
          status: "done",
        },
      ],
      work_steps: [
        { id: "understand", step: "understand", status: "done", duration_ms: 260 },
        {
          id: "retrieve",
          step: "retrieve",
          status: "done",
          duration_ms: 940,
          detail: "Hybrid retrieval returned 5 pages, 1 cited.",
        },
        {
          id: "verify",
          step: "verify",
          status: "done",
          duration_ms: 120,
          detail: "The quoted passage was found on the page.",
        },
        {
          id: "decide",
          step: "decide",
          status: "done",
          duration_ms: 9,
          policy: "active",
          rule_id: "active.explain-current-topic",
        },
        { id: "generate", step: "generate", status: "done", duration_ms: 1850 },
        { id: "cite", step: "cite", status: "done", duration_ms: 48 },
      ],
    },
  },
];

const KERNEL_TURNS: ConversationTurn[] = [
  { message: QUESTION_KERNEL },
  {
    message: ANSWER_KERNEL,
    meta: {
      policy_state: "active",
      reasoning:
        "The question is about kernel layout, which the assignment scores. The active disclosure rule allows structural guidance about the starter layout but not a finished kernel, so I describe the tile and warp mapping and stop before the full implementation.",
      citations: [CITATION_KERNEL],
      sources: [PREVIEW_SOURCES[2]],
      tool_calls: [
        {
          name: "course_search",
          command: ["course_search", "--query", "attention kernel tile", "--top-k", "5"],
          exit_code: 0,
          output:
            "ACS_lecture_4_2026F p.5 (0.88)\nACS_lecture_4_2026F p.6 (0.72)\nACS_lecture_3_2026F p.9 (0.41)",
          status: "done",
        },
        {
          name: "span_verify",
          command: ["span_verify", "--doc", "ACS_lecture_4_2026F", "--page", "5"],
          exit_code: 0,
          output: "1 of 1 quoted passage found on the page.",
          status: "done",
        },
      ],
      work_steps: [
        { id: "understand", step: "understand", status: "done", duration_ms: 300 },
        {
          id: "retrieve",
          step: "retrieve",
          status: "done",
          duration_ms: 1040,
          detail: "Hybrid retrieval returned 5 pages, 1 cited.",
        },
        {
          id: "verify",
          step: "verify",
          status: "done",
          duration_ms: 131,
          detail: "The quoted passage was found on the page.",
        },
        {
          id: "decide",
          step: "decide",
          status: "done",
          duration_ms: 11,
          policy: "active",
          rule_id: "active.explain-current-topic",
        },
        { id: "generate", step: "generate", status: "done", duration_ms: 2210 },
        { id: "cite", step: "cite", status: "done", duration_ms: 52 },
      ],
    },
  },
];

/** Turns for each seeded conversation, keyed by conversation id. */
export const PREVIEW_SESSION_TURNS: Record<string, ConversationTurn[]> = {
  [PREVIEW_SESSIONS[0].id]: PREVIEW_TURNS,
  [PREVIEW_SESSIONS[1].id]: ATTENTION_TURNS,
  [PREVIEW_SESSIONS[2].id]: KERNEL_TURNS,
};

/** The turns a session deep-link opens with; a new chat starts empty. */
export function previewTurnsFor(
  sessionId: string | undefined,
): ConversationTurn[] {
  if (!sessionId) {
    return [];
  }
  return PREVIEW_SESSION_TURNS[sessionId] ?? [];
}

export const PREVIEW_KNOWLEDGE_CARDS: KnowledgeCard[] = [
  {
    chunk_id: "course_project:p001:c00",
    doc_id: "course_project",
    page_no: 1,
    section: "Course Project",
    summary:
      "This page introduces the course project for Advanced AI Computing and Systems, which focuses on building an end-to-end agent system. The project is associated with the Department of Computer Science and Engineering.",
    key_terms: [
      "Course Project",
      "End-to-End Agent System",
      "Advanced AI Computing and Systems",
      "Department of Computer Science and Engineering",
    ],
    study_questions: [
      "What is the primary objective of the course project?",
      "Which department is responsible for the Advanced AI Computing and Systems course?",
    ],
    citations: [
      {
        doc_id: "course_project",
        page_no: 1,
        quote: "Building an End-to-End Agent System",
        bbox_norm: [0.12, 0.18, 0.86, 0.26],
      },
    ],
    model: "qwen3.8-27b",
    prompt_version: "kb-v1",
    build_id: "kb-20261102-01",
    created_at: "2026-11-02T03:02:12+00:00",
  },
  {
    chunk_id: "ACS_lecture_2_2026F:p012:c01",
    doc_id: "ACS_lecture_2_2026F",
    page_no: 12,
    section: "Collective communication",
    summary:
      "MPI collectives move data among all ranks of a communicator. Allreduce is a reduction followed by a broadcast, so every rank ends with the reduced value.",
    key_terms: ["MPI_Allreduce", "MPI_Reduce", "Collective communication", "MPI_COMM_WORLD"],
    study_questions: [
      "What does every rank hold after MPI_Allreduce returns?",
      "When is MPI_Reduce a better choice than MPI_Allreduce?",
    ],
    citations: [
      {
        doc_id: "ACS_lecture_2_2026F",
        page_no: 12,
        quote:
          "MPI_Allreduce combines values from all ranks and distributes the result to all ranks.",
        bbox_norm: [0.08, 0.22, 0.9, 0.3],
      },
    ],
    model: "qwen3.8-27b",
    prompt_version: "kb-v1",
    build_id: "kb-20261102-01",
    created_at: "2026-11-02T03:03:41+00:00",
  },
  {
    chunk_id: "TACC_Toturial:p004:c00",
    doc_id: "TACC_Toturial",
    page_no: 4,
    section: "Submitting a job",
    summary:
      "The TACC SDK submits a task directory with tcloud submit and returns a job id used to inspect the log and download results.",
    key_terms: ["tcloud submit", "Job ID", "slurm_log", "USERDIR"],
    study_questions: [
      "Which command submits the task directory?",
      "Where do downloaded results come from?",
    ],
    citations: [
      {
        doc_id: "TACC_Toturial",
        page_no: 4,
        quote: "Submit the job with tcloud submit and record the Job ID.",
        bbox_norm: [0.1, 0.42, 0.88, 0.5],
      },
    ],
    model: "qwen3.8-27b",
    prompt_version: "kb-v1",
    build_id: "kb-20261102-01",
    created_at: "2026-11-02T03:05:02+00:00",
  },
];

export const PREVIEW_BUILDS: KnowledgeBuild[] = [
  {
    id: "kb-20261102-01",
    state: "ready",
    job_id: "28067",
    records_path: "data/kb/records/kb-20261102-01.jsonl",
    records_count: 8,
    error: null,
    created_at: "2026-11-02T11:58:00+00:00",
    updated_at: "2026-11-02T12:12:00+00:00",
    request: { doc_id: "course_project", max_chunks: 8 },
  },
  {
    id: "kb-20261103-02",
    state: "running",
    job_id: "28114",
    records_path: null,
    records_count: null,
    error: null,
    created_at: "2026-11-03T10:40:00+00:00",
    updated_at: "2026-11-03T10:44:00+00:00",
    request: { doc_id: "ACS_lecture_2_2026F", max_chunks: 8 },
  },
  {
    id: "kb-20261103-03",
    state: "queued",
    job_id: null,
    records_path: null,
    records_count: null,
    error: null,
    created_at: "2026-11-03T10:52:00+00:00",
    updated_at: "2026-11-03T10:52:00+00:00",
    request: { doc_id: "TACC_Toturial", max_chunks: 4 },
  },
  {
    id: "kb-20261101-04",
    state: "failed",
    job_id: "28051",
    records_path: null,
    records_count: null,
    error: "The Qwen job exited before writing records.jsonl: vLLM startup timed out.",
    created_at: "2026-11-01T09:10:00+00:00",
    updated_at: "2026-11-01T10:02:00+00:00",
    request: { doc_id: "ACS_Lecture_0_2026F", max_chunks: 8 },
  },
];

export const PREVIEW_DEADLINES: DeadlineRegistry = {
  version: "deadlines-2026-11-01",
  clock: "2026-11-03T11:00:00+08:00",
  entries: [
    {
      id: "hw2",
      title: "Assignment 2: CUDA attention",
      release: "2026-10-20T09:00:00+08:00",
      due: "2026-11-10T23:59:00+08:00",
      extension_until: null,
      state: "active",
    },
    {
      id: "hw1",
      title: "Assignment 1: MPI GEMM",
      release: "2026-10-06T09:00:00+08:00",
      due: "2026-10-24T23:59:00+08:00",
      extension_until: null,
      state: "post-deadline",
    },
    {
      id: "hw3",
      title: "Assignment 3: inference service",
      release: "2026-11-14T09:00:00+08:00",
      due: "2026-11-28T23:59:00+08:00",
      extension_until: null,
      state: "pre-release",
    },
    {
      id: "hw4",
      title: "Assignment 4: agent system",
      release: "2026-11-01T09:00:00+08:00",
      due: "2026-11-08T23:59:00+08:00",
      extension_until: null,
      state: "active",
    },
    {
      id: "hw0",
      title: "Assignment 0: environment check",
      release: "2026-10-05T09:00:00+08:00",
      due: "2026-10-30T23:59:00+08:00",
      extension_until: "2026-11-05T23:59:00+08:00",
      state: "extension-window",
    },
    {
      id: "quiz-unknown",
      title: "Unregistered quiz",
      release: "",
      due: "",
      extension_until: null,
      state: "unknown",
    },
  ],
};

export const PREVIEW_QUESTIONS: PracticeQuestion[] = [
  {
    id: "q-single",
    type: "single-choice",
    prompt: "Which MPI collective leaves the reduced value on every rank?",
    choices: [
      { value: "a", label: "MPI_Reduce" },
      { value: "b", label: "MPI_Allreduce" },
      { value: "c", label: "MPI_Bcast" },
      { value: "d", label: "MPI_Gather" },
    ],
    points: 1,
    citations: [CITATION_ALLREDUCE],
  },
  {
    id: "q-multiple",
    type: "multiple-choice",
    prompt: "Which statements about the GEMM assignment are true? Select all that apply.",
    choices: [
      { value: "a", label: "The course MPI toolchain compiles the submission." },
      { value: "b", label: "A generic shell tool may run the tests." },
      { value: "c", label: "The test harness reports passing and failing cases." },
      { value: "d", label: "The result only needs to be correct on rank 0." },
    ],
    points: 2,
    citations: [CITATION_COURSE_PROJECT],
  },
  {
    id: "q-true-false",
    type: "true-false",
    prompt: "MPI_Allreduce is always cheaper than MPI_Reduce plus a manual broadcast.",
    choices: [
      { value: "true", label: "True" },
      { value: "false", label: "False" },
    ],
    points: 1,
    citations: [CITATION_ALLREDUCE],
  },
  {
    id: "q-short",
    type: "short-answer",
    prompt: "Explain in one or two sentences why the softmax in attention needs the row maximum.",
    choices: [],
    points: 3,
    citations: [CITATION_COURSE_PROJECT],
  },
  {
    id: "q-code",
    type: "code",
    prompt: "Write the MPI_Allreduce call that sums one double per rank into `global`.",
    choices: [],
    points: 5,
    citations: [CITATION_ALLREDUCE],
    code_template: [
      "double local = compute_partial();",
      "double global = 0.0;",
      "/* your call here */",
    ].join("\n"),
  },
];

export const PREVIEW_GRADING: GradingResult = {
  question_id: "q-code",
  score: 5,
  max_score: 5,
  verdict: "correct",
  explanation:
    "The call names the send buffer, the receive buffer, the count, the datatype, the operation, and the communicator, so every rank leaves with the summed value.",
  citations: [CITATION_ALLREDUCE],
  test_suites: [
    {
      name: "mpi-collectives",
      cases: [
        { name: "one rank matches the serial sum", status: "passed", duration_ms: 412 },
        { name: "four ranks match the serial sum", status: "passed", duration_ms: 508 },
      ],
    },
  ],
};

export const PREVIEW_GRADING_PARTIAL: GradingResult = {
  ...PREVIEW_GRADING,
  score: 2,
  verdict: "partial",
  explanation:
    "The communicator is correct, but the count uses the number of ranks instead of the number of elements, so the test fails for four ranks.",
  test_suites: [
    {
      name: "mpi-collectives",
      cases: [
        { name: "one rank matches the serial sum", status: "passed", duration_ms: 404 },
        {
          name: "four ranks match the serial sum",
          status: "failed",
          duration_ms: 512,
          message: "expected 10.0, received 4.0",
        },
      ],
    },
  ],
};

export const PREVIEW_ANSWER_MARKDOWN = [
  "## MPI_Allreduce",
  "",
  "`MPI_Allreduce` reduces one value per rank and leaves the result on every rank.",
  "",
  "$$C_{ij} = \\sum_{k} A_{ik} B_{kj}$$",
  "",
  "```c",
  "MPI_Allreduce(local, global, count, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);",
  "```",
].join("\n");
