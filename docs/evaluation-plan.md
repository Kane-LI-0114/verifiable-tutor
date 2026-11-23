# Evaluation plan: citation accuracy and knowledge-point coverage

This page designs two experiments that compare the verifiable tutor against a
general web LLM session that has the relevant course PDF uploaded. It is the
operational companion to [product-differentiation.md](product-differentiation.md).

## Baseline

| Group | Material |
|---|---|
| Control | A general web LLM + the relevant course PDFs uploaded to one chat (one or more, as the question requires) |
| Treatment | The verifiable tutor (pre-vectorized corpus, all 13 documents) |

Both groups can answer from material and cite, so the comparison measures
citation correctness, verifiability, and how much material each side can reach
without the user knowing in advance which documents are relevant.

---

## Part 2: citation accuracy

### 2.1 New-question experiment

**Question set**: N factual questions drawn from the course material, three to
five per topic, about 20 in total. Two kinds are included:

- Single-document questions, whose answer sits in one PDF, for example "According
  to Lecture 2, what is the key difference between DRAM and SRAM?"
- Cross-document questions, whose answer spans several documents, for example
  "How does the shared-memory tiling FlashAttention uses relate to the GPU
  memory hierarchy in Lecture 2?"

**Procedure**:

1. Treatment: answer each question with the verifiable tutor and record the
   `[ref_N]` citations.
2. Control: upload the relevant PDFs to the general web LLM (one PDF for a
   single-document question, both PDFs for a cross-document question), ask the
   same question, and ask it to cite the specific PDF location (page or passage).
3. Split both answers into per-claim statements.

**Metrics** (judged by a human or an independent LLM, applied to both groups):

| Metric | Treatment measurement | Control measurement |
|---|---|---|
| Citation precision | whether each `[ref_N]` chunk really contains the claim | whether its "page X" really contains the claim |
| Citation recall | share of claims covered by a `[ref_N]` | share of claims covered by its self-reported citation |
| Support | whether the citation supports the claim (span verifier) | whether the cited text supports the claim (human) |
| Hallucination rate | share of citations pointing at a nonexistent chunk | share pointing at a nonexistent page or passage |
| Cross-document recall | whether cross-document claims are all located | whether cross-document questions are answerable and citable from the uploaded PDFs |

**Expected result**: the two groups are close on single-document questions, but
the control's page citations are generated and can point at the wrong page or
hallucinate, while the treatment's `[ref_N]` come from retrieval and are
programmatically checkable. The remaining gap is material reach: the treatment
automatically retrieves from all 13 documents, while the control can only cite
the PDFs the user knew to upload, and cannot follow a claim to a document the
user did not provide.

### 2.2 Practice experiment

**Procedure**:

1. Both systems generate K questions for the same topic and question types.
2. The control uploads the chapter PDF and is asked to write, per question, a
   reference answer and a citation to the PDF location.

**Metrics**:

- Question groundedness: whether the tested content really exists in the material.
- Reference-answer citation accuracy: whether the reference answer cites the
  right location.
- Reference-answer correctness: whether the reference answer is itself correct.

---

## Part 3: chapter knowledge-point coverage

### 3.1 Chapter

FlashAttention (Tutorial_4), which has five knowledge points in
`config/knowledge_points.yaml`.

### 3.2 Procedure

1. Generate:
   - Treatment: generate N = 10 questions with the verifiable tutor for the
     "FlashAttention" topic (the generator receives the knowledge-point list).
   - Control: upload the `Tutorial_4` PDF to the general web LLM and ask it to generate
     N = 10 questions about FlashAttention.
2. Independently tag every question from both systems onto the five-point list
   with a separate LLM tagger (or a human). The treatment's own
   `knowledge_points` field must not tag itself, or the score is inflated.
3. Compute:

| Metric | Formula | Meaning |
|---|---|---|
| Coverage | covered points / 5 | whether all points are covered |
| Redundancy | question count - covered points | how many questions repeat a point |
| Off-topic rate | questions on out-of-chapter points / total | whether out-of-chapter content was invented |

### 3.3 Expected result

| Dimension | Treatment | Control |
|---|---|---|
| Coverage | high (the point list drives coverage) | medium (driven by the PDF, may miss points or over-focus on one) |
| Redundancy | controllable | may repeat the same point |
| Off-topic | low (closed to the list) | may bring in background beyond the PDF |

### 3.4 Optional cross-grading

Beyond coverage, have each side answer the other side's questions and compare
the scores as an additional measure of question quality.
