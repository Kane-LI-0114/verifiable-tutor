You are writing one chapter of an English revision guide for the CSIT6000V
course at HKUST. The chapter covers one course document and is a key-point
review: summarize and organize the important knowledge points of the document
so a student can review them. Decide the content and the structure yourself;
the only fixed part is how a knowledge point is marked.

Document:
- title: %%TITLE%%
- file: %%FILENAME%%
- pages in this batch: %%PAGE_RANGE%%

The text below is OCR from the document. Each chunk starts with its page number
in the form [page N]. Use only this text. Do not add outside knowledge, and do
not invent facts or page numbers. If the text does not support a point, leave
it out.

Markdown rules:
- A knowledge point is exactly one line that starts with "## ".
- The heading names one knowledge point. Do not use "##" for an introduction,
  a chapter title, a summary, or a group of several points.
- Everything between one "##" heading and the next belongs to that knowledge
  point. Use "###" or deeper, paragraphs, lists, tables, formulas, or code
  however you think best.
- End every "##" heading line with the page where the point is introduced, in
  exactly this form: <!-- page: N -->.
- Do not use an H1 title; the page already shows the document title. Any text
  before the first "##" heading is an optional overview.
- Choose the number of knowledge points and the level of detail yourself. Make
  each point fine-grained enough that a student can mark it as known or unknown
  on its own.
- Skip administrative or meta content: learning outcomes, agendas, roadmaps,
  reading lists, submission logistics, grading policy, and course announcements
  are not knowledge points.
- Write in English.

Rules:
- Do not reveal a complete solution to a current assignment. For an assignment
  document, describe the knowledge points and what the task assesses, not a
  worked answer.
- Output only the chapter Markdown, with no code fence around it.

Text:
%%CHUNKS%%
