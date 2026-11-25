You are designing the revision guide for the CSIT6000V course at HKUST.

Below is one JSON array of the course documents. Each item has doc_id, title,
category, and an English summary.

Group every document into revision themes. Choose as many themes as the
material needs; do not pad the list or force unrelated documents together to
hit a number. A theme is a coherent study area a student would revise together,
for example "GPU memory hierarchy", "Attention and FlashAttention", "LLM
training and inference", "Networks and collective communication", or
"Engineering practice on TACC". Every document must appear in exactly one
theme. Do not invent documents. Use the document summaries as the only
evidence.

Return exactly one JSON object and nothing else:

{"themes": [{"title": "...", "summary": "one or two sentences", "doc_ids": ["..."]}]}

Rules:
- The number of themes follows the material.
- Every doc_id appears exactly once.
- A theme names at least one document.
- Titles are short and in English; summaries are one or two sentences in
  English.
- Order the themes as a sensible study order, not alphabetically.

Documents:
%%DOCUMENTS%%
