# Voice profile: schema, extraction, worked example

A voice profile is the bridge between captured evidence and new copy. It is not a mood
board and not a list of adjectives ("friendly, professional"). Each line names a concrete
choice a writer can make, and cites the quote that proves the genre makes it.

## Schema

| Dimension | Record | Example evidence |
|---|---|---|
| Address & person | Who is spoken to, and as what: you / we / third person; role framing | "Khanmigo is your always-available teaching assistant." |
| Sentence length | Median words per sentence; longest run | Short declaratives, 6–14 words |
| Headline formula | Role + scope, outcome, or task verb; whether it names the product | "Your personal tutor for math and coding" |
| Verb register | Imperative, infinitive, or nominalized; the actual verbs used | ask, sketch, guide, work through, practice |
| Concreteness | Named objects, tasks, artifacts vs abstractions | "upload your homework", "on a shared interactive canvas" |
| Promise strength | Absolute ("always", "never") vs hedged ("helps", "can") | "without giving you direct answers" |
| Numbers policy | Where numbers appear and whether they are sourced | "4,000+ Expert Tutors in 250+ Subjects" |
| Jargon density | Subject terms a student would know vs internal vocabulary | "mastery", "practice", "assessment" |
| Punctuation | Em dashes, colons, parentheses, exclamation marks | Mostly periods; rare colon before a list |
| Proof style | Quotes, ratings, logos, outcome stats, named sources | Press quote + rating; post-session survey |
| Section rhythm | Heading length, paragraph length, list vs prose | 2–4 word headings; one idea per block |
| Avoided moves | What the best sites conspicuously do not do | No "revolutionize", no exclamation marks |

## Synthesis

- **Norm** = at least two of the three captured sites do it. Imitate the norm.
- **Outlier** = one site only. Note it; do not build the voice on it.
- **Weak line** = a line that is vague even on a good site. Use it as a negative example.
- **Lexicon**: collect 10–20 real verbs and nouns from the captures. These are the words the
  genre actually uses; they replace generic marketing vocabulary.

## Worked example — education / AI tutor

Captured 2026-11-13 via `web_fetch`. Sources: `https://www.khanmigo.ai/`,
`https://www.brilliant.org/`, `https://www.tutor.com/`. Failed and therefore not used:
Quizlet (403 captcha), Coursera (JS shell, title only), icourse163 (privacy modal + footer
only).

**Norm across the three**

- Second person dominates: "your always-available teaching assistant" (Khanmigo), "Your
  personal tutor for math and coding" (Brilliant). Tutor.com speaks to institutions
  ("Partner with us", "your institution"), which fits its B2B angle.
- Headlines name a role or a task, not a feeling: "teaching assistant", "personal tutor",
  "Online Tutoring That Accelerates Student Achievement".
- The mechanism is described with concrete verbs: "asks guiding questions, sketches on your
  screen, and helps you work through each step" (Brilliant); "guides learners to find the
  answer themselves" (Khanmigo).
- Differentiation often works by naming the failure mode: "without giving you direct
  answers" (Khanmigo), "not a cheating machine" (Brilliant).
- Proof is specific when it is good: "4,000+ Expert Tutors in 250+ Subjects" (Tutor.com),
  a named press quote and a 4-star rating (Khanmigo).

**Weak lines — do not imitate**

- "Online Tutoring That Accelerates Student Achievement" — an outcome claim with no
  mechanism.
- "Powerful insights, real results", "Unmatched tutor quality" — superlatives standing in
  for evidence.
- Long institutional noun stacks: "Real-time data and actionable analytics to measure impact
  and continuously improve outcomes".

**Lexicon from the captures**

tutor, teaching assistant, guided questions, step by step, work through, practice, mastery,
assessment, feedback, progress, course material, homework, test prep.

**Implications for Verifiable Tutor**

- Lead with the mechanism the product actually has: answers cite a page and a quoted span,
  and the span is checked against the page text. That is more distinctive than "AI-powered".
- Say what it will not do (invent answers, reveal what the assignment policy forbids). The
  genre rewards that honesty.
- Numbers only when real. This project has evaluation results, not "thousands of students";
  cite the evaluation or say nothing.
- Chinese: address the student directly, verb first, no "赋能/助力/开启学习之旅". A good
  model is the existing line "以课程材料为依据、引用可核查的答疑。"

**Profile status**: reusable for Tier B microcopy in this project until 2027-02-13 (three
months). After that, or when the product's positioning changes, recapture.
