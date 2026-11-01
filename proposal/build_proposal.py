#!/usr/bin/env python3
"""Build the CSIT6000V 2-page project proposal (.docx + .md master).

Version 1 is the submitted October 27, 2026 proposal and stays frozen.
Version 2 is the October 30, 2026 revision. Version 3 is the November 1,
2026 revision: it writes new files and leaves versions 1 and 2 untouched.
"""
import argparse
import os, subprocess
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(HERE, "figs")

_parser = argparse.ArgumentParser(description="Build the CSIT6000V project proposal.")
_parser.add_argument("--version", type=int, choices=(1, 2, 3), default=1,
                     help="1 builds the submitted proposal; 2 or 3 build the revisions.")
VERSION = _parser.parse_args().version

if VERSION == 1:
    DOCX = os.path.join(HERE, "CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx")
    MD = os.path.join(HERE, "proposal.md")
    FIG2 = os.path.join(FIGS, "fig2_components.png")
    DATE = "October 27, 2026"
    HEADER_LINE = "Project Proposal \u00b7 Topic Selection"
    REVISION_NOTE = None
    COURSE_LINE = ("CSIT6000V \u2014 Advanced AI Computing and Systems \u00b7 Fall 2026 "
                   "\u00b7 Instructor: Prof. Kai Chen")
    COURSE_LINE_MD = "CSIT6000V \u2014 Advanced AI Computing and Systems \u00b7 Fall 2026"
    FIG2_WIDTH = 14.9
    CAPTION2 = "Figure 2. Containers and components of the agent."
    ALT2_TEXT = ("Container and component diagram of the agent backend, model serving job, "
                 "stores, and tools.")
    FIG1 = os.path.join(FIGS, "fig1_usecase.png")
    FIG1_WIDTH = 5.2
    ALT1_TEXT = "Use case diagram: student and instructor/TA actors and six agent use cases."
    CAPTION1 = "Figure 1. Use cases of the tutoring agent."
    TBL_CAPTION = "Table 1. Gantt-style work plan (W1\u2013W4)."
    CAVEAT = None
    PROP_SUBJECT = "CSIT6000V Project Proposal (Topic Selection)"
    PROP_COMMENTS = "Course project proposal, Fall 2026"
else:
    DOCX = os.path.join(HERE, "CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.docx")
    MD = os.path.join(HERE, "proposal_v2.md")
    FIG2 = os.path.join(FIGS, "fig2_components_v2.png")
    DATE = "October 30, 2026"
    HEADER_LINE = "Project Proposal \u00b7 Topic Selection"
    REVISION_NOTE = None
    COURSE_LINE = ("CSIT6000V \u00b7 Advanced AI Computing and Systems \u00b7 Fall 2026 "
                   "\u00b7 Instructor: Prof. Kai Chen")
    COURSE_LINE_MD = "CSIT6000V \u00b7 Advanced AI Computing and Systems \u00b7 Fall 2026"
    FIG2_WIDTH = 14.4
    CAPTION2 = ("Figure 2. Containers and components of the agent: local backend, "
                "external APIs, and offline TACC batch jobs with no hosted service.")
    ALT2_TEXT = ("Container and component diagram: a local backend and UI, external model "
                 "APIs, and TACC offline batch jobs with no hosted service.")
    FIG1 = os.path.join(FIGS, "fig1_usecase.png")
    FIG1_WIDTH = 5.2
    ALT1_TEXT = "Use case diagram: student and instructor/TA actors and six agent use cases."
    CAPTION1 = "Figure 1. Use cases of the tutoring agent."
    CAVEAT = ("The models, services, and batch layout named here reflect the current plan "
              "and may change as development proceeds.")
    TBL_CAPTION = "Table 1. Gantt-style work plan (W1-W4)."
    PROP_SUBJECT = "CSIT6000V Project Proposal (Topic Selection)"
    PROP_COMMENTS = "Course project proposal, Fall 2026"

# ---------------------------------------------------------------- content
TITLE = "Verifiable AI Tutoring on TACC"
SUBTITLE = ("A course-grounded agent with evidence-checked answers, executable practice "
            "labs, and enforced course policy")

MOTIVATION = (
    "In CSIT6000V, students absorb dense lecture and tutorial material and then apply it in "
    "individual coding assignments, but support is uneven: TAs are scarce, and generic "
    "assistants cannot ground answers in the course\u2019s own slides or respect its integrity "
    "rules. Answers are not verifiable against the slides, practice at assignment scale risks "
    "leaking solutions, and disclosure behaviour is left to a model\u2019s discretion. We treat these as one systems problem: every output must be "
    "checkable \u2014 text claims against cited page spans, code artifacts against executable "
    "tests, and disclosure against a dated policy (Figure 1). The scenario is deliberately narrow: "
    "one course\u2019s own materials, assignments, and deadlines."
)

TASK = [
    ("Two actors use the agent. A student can (i) ask course questions and receive an answer that "
     "cites the exact page and quoted span; (ii) request a review outline or a self-test quiz on a "
     "topic; (iii) practise with a generated exercise at the scale and environment of the "
     "corresponding assignment, receiving a reference solution, tests, and a stepwise explanation; "
     "and (iv) submit their own solution and receive line-anchored teaching. An instructor or TA "
     "maintains the deadline registry."),
    ("Disclosure follows a five-state policy: pre-release, active, extension window, post-deadline, and "
     "unknown. Before the deadline the agent refuses complete homework solutions and offers hints; "
     "it explains user-provided solutions only at the level of what was provided and never fills in "
     "missing parts; after the deadline it replaces refusal with full teaching and a verified solution. Insufficient "
     "evidence leads to abstention, not guessing."),
]

SYSTEM = [
    ("Figure 2 shows the containers. A browser UI talks to an agent backend submitted as a TACC CPU "
     "job, which calls the course Qwen service on a GPU job through a model-client abstraction."),
    ("Evidence. Course PDFs are parsed with an OCR stage chosen during week one (existing transcripts "
     "as fallback) into page- and section-aware chunks, indexed by dense embeddings (computed in batches and cached; "
     "model chosen during week one) and BM25; retrieval fuses both and reranking is "
     "optional. A deterministic verifier then checks that every quoted span occurs on its cited "
     "page, triggering one repair round or abstention."),
    ("Artifacts. A practice pack mirrors the target assignment\u2019s environment \u2014 first pack: "
     "MPI/GEMM with the same toolchain, Makefile, public datasets and sdk-test-style harness. A "
     "generated reference solution is accepted only after it compiles and passes the pack\u2019s "
     "tests, so practice answers are verified rather than asserted. Later assignments add packs; GPU "
     "packs are verified in a batch window and cached."),
    ("Policy. The gate is code, not a prompt: a versioned registry stores each assignment\u2019s "
     "release and due dates with extensions, an intent classifier routes requests, and every "
     "decision is logged. This makes disclosure testable and resistant to prompt injection."),
    ("Teaching. Explanations cite the artifacts they teach \u2014 page spans, code lines, test "
     "outcomes \u2014 and never invent missing content before the deadline."),
    ("Deployment. The model client keeps the TACC service primary (vLLM, Qwen3.8-27B-AWQ-INT4, "
     "TP=2, 32K context, at most four concurrent requests); external LLM and search APIs are "
     "optional, labelled, and cached for baselines. Traces, tests, and results follow the required "
     "execution path from task to visible result."),
]

EVAL = [
    ("We ask four questions on an in-repository benchmark. RQ1 evidence fidelity: citation span "
     "accuracy (deterministic) and faithfulness (human-checked support rate). RQ2 practice "
     "verifiability: the share of generated exercises whose reference solution compiles and passes "
     "course-style tests, plus environment alignment and cost per exercise. RQ3 disclosure "
     "correctness: behaviour across the five policy states, including a deadline extension, and an "
     "adversarial set of false \u201cdeadline passed\u201d claims, TA impersonation, role-play, and "
     "pasted \u201cofficial\u201d solutions, compared with a prompt-only policy baseline. RQ4 cost: "
     "end-to-end latency, model calls per request, and a retrieval ablation over BM25, dense, and "
     "hybrid variants."),
    ("The benchmark holds fifty course questions, ten policy scenarios, and two practice packs; "
     "later-released sessions are held out as unseen data. Ablations isolate the span verifier, the "
     "code-level gate, and the hybrid index. Failure analysis groups errors by cause \u2014 OCR "
     "corruption, figure-only slides, retrieval misses, context overflow in long sessions, "
     "test-failing generated solutions, and policy bypasses \u2014 and analyses the dominant mode. "
     "Runs are reproducible with temperature 0, cached retrieval snapshots and responses, and an "
     "injected clock for policy tests."),
]

MILESTONES = ("Four one-week workstreams move from infrastructure to full evaluation (Table 1); "
            "deliverables are the code repository, evaluation report, and demo.")

GANTT = [
    ("Corpus and OCR pipeline", ["X", "", "", ""]),
    ("Hybrid index and retrieval", ["X", "X", "", ""]),
    ("Span verifier", ["", "X", "", ""]),
    ("Policy engine and registry", ["", "X", "X", ""]),
    ("Practice pack and tests", ["", "", "X", ""]),
    ("Explainer", ["", "", "X", ""]),
    ("UI and replay mode", ["", "", "X", "X"]),
    ("Evaluation, report, demo", ["", "", "", "X"]),
]

RISKS = (
    "OCR and embedding choices are unsettled: existing transcripts and cached embeddings bound the "
    "risk. The assignment toolchain may not be reachable from the project client job: week-one "
    "validation with a documented fallback. GPU pack verification competes with model serving: "
    "dedicated batch windows. External APIs add cost and availability risk: optional, cached, and "
    "never primary. Assignments may be reused across years: the registry is configurable and "
    "defaults conservative. Prompt injection: a code-level gate plus adversarial tests."
)

REFS = [
    "Course Project Brief, CSIT6000V Advanced AI Computing and Systems, Fall 2026.",
    "TACC@HKUST Public Environment Guide, CSIT6000V, Fall 2026.",
    "S. Robertson and H. Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. "
    "Foundations and Trends in Information Retrieval, 3(4):333\u2013389, 2009. "
    "doi:10.1561/1500000019.",
    "Assignment 1: MPI Programming, CSIT6000V, Fall 2026.",
]

# --------------------------------------------------------- version 2 content
# The revision records the delivered topology (local backend, TACC offline
# compute) and the task-oriented positioning. Version 1 stays untouched.
V2_MOTIVATION = (
    "In CSIT6000V, students absorb dense lecture and tutorial material and then apply it in "
    "individual coding assignments, but support is uneven: TAs are scarce, and generic "
    "assistants cannot ground answers in the course\u2019s own slides or respect its integrity "
    "rules. Answers are not verifiable against the slides, practice at assignment scale risks "
    "leaking solutions, and disclosure behaviour is left to a model\u2019s discretion. We treat "
    "these as one systems problem: every output must be checkable, with text claims checked "
    "against cited page spans, code artifacts against executable tests, and disclosure against "
    "a dated policy (Figure 1). The scenario is deliberately narrow: one course\u2019s own "
    "materials, assignments, and deadlines."
)

V2_TASK = [
    ("Two actors use the agent. A student can (i) ask course questions and receive an answer "
     "that cites the exact page and quoted span; (ii) request a review outline or a self-test "
     "quiz on a topic; (iii) practise with a generated exercise at the scale and environment of "
     "the corresponding assignment, receiving a reference solution, tests, and a stepwise "
     "explanation; (iv) submit their own solution and receive line-anchored teaching; and (v) "
     "ask by voice, attach audio, and play spoken answers through the MiMo audio models. An "
     "instructor or TA maintains the deadline registry."),
    TASK[1],
]

V2_SYSTEM = [
    ("Figure 2 shows the containers. A React browser UI talks to a FastAPI agent backend on "
     "the developer laptop, which runs a typed LangGraph workflow, calls external "
     "OpenAI-compatible model APIs, and reads a local mirror of the OCR pages and index vectors "
     "that TACC produces offline. The required execution path, from task to visible result, runs "
     "on the laptop: enter the task, watch progress, and review the answer with its evidence."),
    ("Evidence. Course PDFs are parsed by a TACC OCR batch job with PaddleOCR-VL into page "
     "records with page numbers, block boxes, and page images; the week-one OCR and whole-PDF "
     "parse spikes passed in week one. Page- and section-aware chunks are embedded with "
     "BGE-M3 in a TACC index job and indexed with BM25; both artifacts are downloaded into the "
     "laptop mirror. A deterministic verifier checks that every quoted span occurs on its cited "
     "page, triggering one repair round or abstention."),
    ("Artifacts. A practice pack mirrors the target assignment environment: MPI/GEMM with the "
     "same toolchain, Makefile, public datasets, and sdk-test-style harness. A generated "
     "reference solution is accepted only after it compiles and passes the pack tests in a TACC "
     "execution job, and verified answers are cached. A CUDA attention pack is best effort (P2)."),
    ("Policy. The gate is code, not a prompt: the agent runs as a typed LangGraph StateGraph "
     "over typed tools with no generic shell; a versioned registry stores each assignment "
     "release and due dates with extensions, an intent classifier routes requests, and every "
     "decision is logged. This makes disclosure testable and resistant to prompt injection."),
    ("Teaching and work chain. Explanations cite the artifacts they teach, page spans, code "
     "lines, and test outcomes, and never invent missing content before the deadline; the work "
     "chain and its JSONL trace expose each step for review and replay."),
    ("Deployment. Text generation uses external OpenAI-compatible APIs (DeepSeek primary; "
     "MiMo selectable for chat, audio, and speech) with same-model retries and no automatic "
     "cross-model fallback; every call is labelled and cached. TACC is an offline compute "
     "resource: submitted batch jobs produce the OCR records, the embedding index, execution "
     "results, and evaluation evidence, and each job exits when finished. No service is hosted "
     "on TACC; the course Qwen model is an optional offline batch baseline. JSONL traces remain "
     "canonical."),
]

V2_EVAL = [
    ("We ask four questions on an in-repository benchmark. This is a task-oriented project: "
     "it targets tutoring-task performance against baselines (an external chatbot for the "
     "self-test loop, a prompt-only policy for disclosure), with latency and cost reported as "
     "secondary metrics (RQ4). RQ1 evidence fidelity: citation span accuracy (deterministic) "
     "and human-checked faithfulness. RQ2a asks whether generated questions have reference "
     "answers that compile and pass course-style tests and cite the material; RQ2b compares "
     "the agent's grading agreement with developer ground truth and the chatbot baseline, with "
     "a capability gap table. RQ3 disclosure correctness covers the five policy states, a "
     "deadline extension, and adversarial cases: false deadline claims, TA impersonation, "
     "role-play, and pasted official solutions. RQ4 reports latency, model calls per request, "
     "and a BM25, dense, and hybrid ablation."),
    ("The benchmark holds fifty course questions, ten policy scenarios, one MPI/GEMM practice "
     "pack, and a shared self-test grading set; later-released sessions are held out. Failure "
     "analysis groups errors by cause: OCR corruption, figure-only slides, retrieval misses, "
     "context overflow, test-failing generated solutions, and policy bypasses, and analyses the "
     "dominant mode. Runs use temperature 0, cached retrieval snapshots, and an injected clock."),
]

V2_MILESTONES = ("Four one-week workstreams move from infrastructure to full evaluation "
                 "(Table 1). Deliverables are the code repository, evaluation report, tested "
                 "demo, and final presentation.")

V2_RISKS = ("TACC batch work is queue-bound and capped at one hour: schedule corpus, index, "
            "and execution jobs early, keep them resumable, and cache their outputs. External "
            "APIs add cost and availability risk: calls are labelled, cached, and retried only "
            "on the same model, so no rerun needs a paid call. The live demo depends on the "
            "laptop: a documented runbook and a replay fallback cover a machine or network "
            "failure. OCR quality is checked against page images, and prompt injection is "
            "handled by the code-level gate plus adversarial tests.")

V2_REFS = [
    "Course Project Brief and staff clarifications, CSIT6000V, Fall 2026.",
    "TACC@HKUST Public Environment Guide, CSIT6000V, Fall 2026.",
    "S. Robertson and H. Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. "
    "Found. Trends Inf. Retr., 3(4):333-389, 2009. doi:10.1561/1500000019.",
    "Assignment 1: MPI Programming, CSIT6000V, Fall 2026.",
]


# --------------------------------------------------------- version 3 content
# Version 3 records the 2026-11-01 TACC requirement: TACC is a required
# model-serving backend, and Qwen runs there as an offline text-processing
# backend for the course knowledge base. Versions 1 and 2 stay untouched.
V3_TASK = [
    ("Two actors use the agent. A student can (i) ask course questions and receive an answer "
     "that cites the exact page and quoted span; (ii) request a review outline or a self-test "
     "quiz on a topic; (iii) practise with a generated exercise at the scale and environment of "
     "the corresponding assignment, receiving a reference solution, tests, and a stepwise "
     "explanation; (iv) submit their own solution and receive line-anchored teaching; (v) "
     "ask by voice, attach audio, and play spoken answers through the MiMo audio models; and "
     "(vi) browse the course knowledge base that TACC enriches offline. An instructor or TA "
     "maintains the deadline registry and triggers knowledge-base builds."),
    TASK[1],
]

V3_SYSTEM = [
    ("Figure 2 shows the containers. A React browser UI talks to a FastAPI agent backend on "
     "the developer laptop, which runs a typed LangGraph workflow and calls external "
     "OpenAI-compatible APIs for interactive answers. TACC is a required model-serving "
     "backend: submitted GPU jobs run the embedding model and Qwen text processing; the "
     "backend submits a job, waits for its result, and uses it. The required execution path, "
     "from task to visible result, runs on the laptop: enter the task, watch progress, and "
     "review the answer with its evidence."),
    ("Evidence. Course PDFs are parsed by a TACC OCR job with PaddleOCR-VL into page records "
     "with block boxes and page images. Page-aware chunks are embedded with BGE-M3 and indexed "
     "with BM25 in a TACC job; the artifacts are downloaded to the laptop. A deterministic "
     "verifier checks every quoted span against its cited page, with one repair round or "
     "abstention."),
    ("Knowledge base. Qwen on TACC is an offline text-processing backend: one submitted GPU "
     "job per build shard reads course chunks from USERDIR, generates cited knowledge cards (summary, "
     "key concepts, study questions) as JSONL, and exits. The local backend polls, downloads, "
     "validates, and stores the records; no port forwarding or inbound service is used."),
    ("Artifacts. The MPI/GEMM practice pack mirrors the assignment toolchain, Makefile, "
     "datasets, and test harness; a generated reference solution is accepted only after it "
     "compiles and passes the pack tests in a TACC execution job. A CUDA pack is best effort "
     "(P2)."),
    ("Policy. The gate is code, not a prompt: a typed LangGraph StateGraph over typed tools, a "
     "versioned deadline registry, an intent classifier, and a decision log make disclosure "
     "testable and resistant to prompt injection; explanations cite page spans, code lines, or "
     "test outcomes."),
    ("Deployment. Interactive text generation uses external APIs (DeepSeek primary; MiMo "
     "selectable) with same-model retries and caching. TACC model serving is required and "
     "batched: the embedding index and Qwen knowledge-base jobs are reached only through job "
     "submission, and their outputs are downloaded and cached; no SSH forwarding or inbound "
     "service is used."),
]

V3_EVAL = [
    ("We ask four questions on an in-repository benchmark. This is a task-oriented project: it "
     "targets tutoring-task performance against baselines (an external chatbot for the "
     "self-test loop, a prompt-only policy for disclosure), with efficiency as a secondary "
     "metric (RQ4). RQ1 tests citation accuracy and faithfulness; RQ2a tests reference answers "
     "that compile and pass course-style tests; RQ2b compares grading agreement with developer "
     "ground truth and the chatbot; RQ3 covers five policy states and adversarial cases; RQ4 "
     "reports latency, model calls, and the BM25, dense, and hybrid ablation."),
    ("The benchmark holds fifty course questions, ten policy scenarios, one MPI/GEMM pack, and "
     "a shared grading set. The required TACC workflow is demonstrated end to end: one "
     "knowledge-base build job per document batch is submitted, its JSONL records are "
     "downloaded and validated, and the resulting knowledge base feeds a review outline; the "
     "report records queue, cold-start, build time, and schema validity. Failure analysis groups "
     "errors by cause: OCR corruption, figure-only slides, retrieval misses, context overflow, "
     "test-failing generated solutions, policy bypasses, and malformed Qwen records."),
]

V3_MILESTONES = ("Four one-week workstreams move from infrastructure to full evaluation "
                 "(Table 1). Deliverables are the code repository, evaluation report, tested "
                 "demo, and final presentation; the demo includes a TACC Qwen knowledge-base "
                 "build used by the agent.")

V3_RISKS = ("TACC jobs are queue-bound and capped at one hour: schedule the embedding and "
            "knowledge-base jobs early, shard by document, keep them resumable, and pre-build "
            "the demo knowledge base. Qwen output can be malformed: records are schema-validated "
            "and repaired once. External APIs add cost and availability risk: calls are labelled, "
            "cached, and retried only on the same model. A laptop failure is covered by the "
            "runbook and replay fallback; OCR quality is spot-checked, and prompt injection is "
            "handled by the gate plus adversarial tests.")

V3_REFS = [
    "Course Project Brief and staff clarifications (2026-10-28, 2026-10-30, 2026-11-01), "
    "CSIT6000V, Fall 2026.",
    "TACC@HKUST Public Environment Guide, CSIT6000V, Fall 2026.",
    "S. Robertson and H. Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. "
    "Found. Trends Inf. Retr., 3(4):333-389, 2009. doi:10.1561/1500000019.",
    "Assignment 1: MPI Programming, CSIT6000V, Fall 2026.",
]

if VERSION == 2:
    MOTIVATION = V2_MOTIVATION
    TASK = V2_TASK
    SYSTEM = V2_SYSTEM
    EVAL = V2_EVAL
    MILESTONES = V2_MILESTONES
    RISKS = V2_RISKS
    REFS = V2_REFS
elif VERSION == 3:
    MOTIVATION = V2_MOTIVATION
    TASK = V3_TASK
    SYSTEM = V3_SYSTEM
    EVAL = V3_EVAL
    MILESTONES = V3_MILESTONES
    RISKS = V3_RISKS
    REFS = V3_REFS


if VERSION == 3:
    DOCX = os.path.join(HERE, "CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.docx")
    MD = os.path.join(HERE, "proposal_v3.md")
    FIG1 = os.path.join(FIGS, "fig1_usecase_v3.png")
    FIG1_WIDTH = 4.7
    FIG2 = os.path.join(FIGS, "fig2_components_v3.png")
    DATE = "November 1, 2026"
    HEADER_LINE = "Project Proposal \u00b7 Topic Selection"
    REVISION_NOTE = None
    COURSE_LINE = ("CSIT6000V \u00b7 Advanced AI Computing and Systems \u00b7 Fall 2026 "
                   "\u00b7 Instructor: Prof. Kai Chen")
    COURSE_LINE_MD = "CSIT6000V \u00b7 Advanced AI Computing and Systems \u00b7 Fall 2026"
    FIG2_WIDTH = 14.4
    ALT1_TEXT = ("Use case diagram: student and instructor/TA actors, the tutoring use cases, "
                 "and the knowledge-base build and browse use cases.")
    CAPTION1 = "Figure 1. Use cases of the tutoring agent and the knowledge base."
    CAPTION2 = ("Figure 2. Containers and components of the agent: local backend, external APIs, "
                "and required TACC model-serving jobs for embeddings and the Qwen knowledge base.")
    ALT2_TEXT = ("Container and component diagram: a local backend and UI, external model APIs, "
                 "and TACC model-serving jobs for embeddings and Qwen knowledge-base enrichment.")
    CAVEAT = ("Models, service versions, and batch sizes may change; the required TACC "
              "model-serving path and job-submission access are fixed.")
    TBL_CAPTION = "Table 1. Gantt-style work plan (W1-W4)."
    PROP_SUBJECT = "CSIT6000V Project Proposal (Topic Selection)"
    PROP_COMMENTS = "Course project proposal, Fall 2026"

# ---------------------------------------------------------------- helpers
BODY_PT, SMALL_PT, CAP_PT = 10.5, 8.5, 7.5
TNR = "Times New Roman"


def set_run(run, size=BODY_PT, bold=False, italic=False, font=TNR):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), font)


def para(container, text, size=BODY_PT, bold=False, italic=False, align="justify",
         before=0, after=2.5, keep_next=False, line=1.0):
    p = container.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.keep_with_next = keep_next
    pf.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    if text:
        set_run(p.add_run(text), size=size, bold=bold, italic=italic)
    return p


def heading(doc, text):
    p = para(doc, text, size=11, bold=True, align="left", before=3, after=1, keep_next=True)
    p.style = doc.styles["Heading 1"]
    for r in p.runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    return p


def caption(doc, text, after=2):
    return para(doc, text, size=CAP_PT, italic=True, align="center", before=1, after=after)


def add_picture_centered(doc, path, width_cm, before=2, after=1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(width_cm))
    return p


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def cell_text(cell, text, bold=False, size=8.0, align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.0
    set_run(p.add_run(text), size=size, bold=bold)


def set_alt(p, text):
    for docPr in p._p.iter(qn("wp:docPr")):
        docPr.set("descr", text)


def add_page_field(paragraph, size=8.5):
    run = paragraph.add_run()
    set_run(run, size=size)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size * 2))); rpr.append(sz)
    rf = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), TNR)
    rpr.insert(0, rf)
    r.append(rpr)
    t = OxmlElement("w:t"); t.text = "1"; r.append(t)
    fld.append(r)
    paragraph._p.append(fld)


# ---------------------------------------------------------------- build
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.0)
sec.left_margin = sec.right_margin = Cm(2.0)
sec.footer_distance = Cm(1.0)

normal = doc.styles["Normal"]
normal.font.name = TNR
normal.font.size = Pt(BODY_PT)
normal.paragraph_format.space_after = Pt(3)
normal.paragraph_format.line_spacing = 1.0

# footer: Page X
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.paragraph_format.space_before = Pt(0)
fp.paragraph_format.space_after = Pt(0)
set_run(fp.add_run("Page "), size=8.5)
add_page_field(fp)

# title block (compact: 6 lines, plus one revision line for version 2)
para(doc, COURSE_LINE, size=9.5, align="center", after=0)
para(doc, HEADER_LINE, size=9.5, align="center", after=4)
para(doc, TITLE, size=15, bold=True, align="center", after=2)
if VERSION == 1:
    para(doc, "A course-grounded agent with evidence-checked answers,",
         size=10, italic=True, align="center", after=0)
    para(doc, "executable practice labs, and enforced course policy",
         size=10, italic=True, align="center", after=3)
else:
    para(doc, "A course-grounded agent with evidence-checked answers, executable practice labs, "
              "and enforced course policy",
         size=9.5, italic=True, align="center", after=3)
para(doc, f"LI Jinchuan (21188271) \u00b7 TIAN Yujia (21201619) \u00b7 XIE Yifeng (21322152) \u00b7 {DATE}",
     size=9.5, align="center", after=2 if REVISION_NOTE else 4)
if REVISION_NOTE:
    para(doc, REVISION_NOTE, size=8.5, italic=True, align="center", after=4)

# 1 Motivation
heading(doc, "1. Motivation and Problem")
para(doc, MOTIVATION)
p_fig1 = add_picture_centered(doc, FIG1, FIG1_WIDTH)
set_alt(p_fig1, ALT1_TEXT)
caption(doc, CAPTION1)

# 2 Task
heading(doc, "2. Task Definition and Outputs")
for t in TASK:
    para(doc, t)

# 3 System
heading(doc, "3. Proposed System")
para(doc, SYSTEM[0])
p_fig2 = add_picture_centered(doc, FIG2, FIG2_WIDTH)
set_alt(p_fig2, ALT2_TEXT)
caption(doc, CAPTION2, after=4)
for t in SYSTEM[1:]:
    para(doc, t)
if CAVEAT:
    para(doc, CAVEAT, size=SMALL_PT, italic=True, align="justify", before=1, after=3)

# 4 Evaluation
heading(doc, "4. Evaluation Plan")
for t in EVAL:
    para(doc, t)

# 5 Milestones + Gantt
heading(doc, "5. Milestones")
para(doc, MILESTONES, after=2)
rows = 1 + len(GANTT)
tbl = doc.add_table(rows=rows, cols=5)
tbl.style = "Table Grid"
tbl.autofit = False
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
widths = [Cm(7.0), Cm(2.0), Cm(2.0), Cm(2.0), Cm(2.0)]
for c in range(5):
    tbl.columns[c].width = widths[c]
for r in range(rows):
    for c in range(5):
        tbl.rows[r].cells[c].width = widths[c]
hdr = ["Workstream", "W1", "W2", "W3", "W4"]
for c, text in enumerate(hdr):
    cell_text(tbl.rows[0].cells[c], text, bold=True, size=8.0,
              align=WD_ALIGN_PARAGRAPH.LEFT if c == 0 else WD_ALIGN_PARAGRAPH.CENTER)
    shade(tbl.rows[0].cells[c], "D9D9D9")
for i, (name, weeks) in enumerate(GANTT, start=1):
    cell_text(tbl.rows[i].cells[0], name, size=8.0, align=WD_ALIGN_PARAGRAPH.LEFT)
    for j, mark in enumerate(weeks, start=1):
        cell_text(tbl.rows[i].cells[j], mark, size=8.0)
        if mark:
            shade(tbl.rows[i].cells[j], "BFBFBF")
    tbl.rows[i].height = Cm(0.38)
tbl.rows[0].height = Cm(0.38)
caption(doc, TBL_CAPTION, after=4)

# 6 Risks
heading(doc, "6. Risks and Mitigation")
para(doc, RISKS)

# References
heading(doc, "References")
for i, ref in enumerate(REFS, start=1):
    para(doc, f"[{i}] {ref}", size=8.0, after=0.5)

cp = doc.core_properties
cp.title = TITLE
cp.author = "LI Jinchuan (21188271); TIAN Yujia (21201619); XIE Yifeng (21322152)"
cp.subject = PROP_SUBJECT
cp.comments = PROP_COMMENTS
doc.save(DOCX)
print("saved", DOCX)

# ---------------------------------------------------------------- md master
with open(MD, "w", encoding="utf-8") as f:
    f.write(f"# {TITLE}\n\n{SUBTITLE}\n\n")
    f.write(f"LI Jinchuan (21188271) · TIAN Yujia (21201619) · XIE Yifeng (21322152) · {DATE}\n\n")
    if REVISION_NOTE:
        f.write(f"*{REVISION_NOTE}*\n\n")
    f.write(f"{COURSE_LINE_MD}\n\n")
    f.write("## 1. Motivation and Problem\n\n" + MOTIVATION + "\n\n")
    f.write(f"![Figure 1](figs/{os.path.basename(FIG1)})\n\n")
    f.write("## 2. Task Definition and Outputs\n\n" + "\n\n".join(TASK) + "\n\n")
    f.write("## 3. Proposed System\n\n" + "\n\n".join(SYSTEM) + "\n\n")
    if CAVEAT:
        f.write(f"*{CAVEAT}*\n\n")
    f.write(f"![Figure 2](figs/{os.path.basename(FIG2)})\n\n")
    f.write("## 4. Evaluation Plan\n\n" + "\n\n".join(EVAL) + "\n\n")
    f.write("## 5. Milestones\n\n" + MILESTONES + "\n\n")
    f.write("| Workstream | W1 | W2 | W3 | W4 |\n|---|---|---|---|---|\n")
    for name, weeks in GANTT:
        f.write("| " + name + " | " + " | ".join(m if m else " " for m in weeks) + " |\n")
    f.write("\n## 6. Risks and Mitigation\n\n" + RISKS + "\n\n")
    f.write("## References\n\n" + "\n".join(f"[{i}] {r}" for i, r in enumerate(REFS, 1)) + "\n")
print("saved", MD)
