# Web copy guide

This guide tells an agent how to write, review, and place user-facing text in the
Verifiable Tutor web app. It governs every string in
`src/verifiable_tutor/ui/web/src/lib/i18n/en.ts` and `zh.ts`, and the few strings that are
still hardcoded in components.

The guide is evidence-based. The voice rules below are drawn from five live captures made
on 2026-11-13, and from the project's own banned list. Section 8 is the current audit of
this product, not a permanent instruction. Re-audit when a page changes.

The one rule: if the interface can show it, show it. If the user must decide, say it. If
neither, write nothing.

## 1. How to use this document

For a new string:

1. Classify the surface with section 5.
2. Check the factual claim against the claims ledger in section 9.
3. Write the English in `en.ts`, then the Chinese in `zh.ts` for the same intent.
4. Run the checks in section 11.

For a review, run the checklist in section 7.6 and the banned list in section 7.5.

For a new page or a positioning change, run the research again: at least three live sites,
captured with URL, method, timestamp, and quotes. Search snippets and memory do not count.

## 2. Product facts the copy may use

| Fact | Source |
|---|---|
| The product is a course tutor for CSIT6000V at HKUST, Fall 2026. | `docs/prd.md`, `README.md` |
| Students ask a question and receive an answer with numbered sources. | `docs/prd.md` G1 |
| A source opens the course page image and the quoted text. | `docs/prd.md` G1, corpus page route |
| The work chain records each step of an answer: read, find, check, decide, write, cite. | `docs/prd.md`, `GLOSSARY.md` |
| A dated assignment registry decides what the tutor may reveal. | `docs/prd.md` G2 |
| An unknown assignment makes the tutor abstain, not guess. | `docs/prd.md` G2 |
| Practice questions carry a reference answer and sources. | `docs/prd.md` G3 |
| Code answers run as a TACC job under the course account, not in an isolated sandbox. | `docs/prd.md`, `docs/tacc-notes.md` |
| The knowledge base holds the course documents, indexed text, and summaries. | `docs/prd.md` |
| The instructor surface lists knowledge builds and the deadline registry. | `docs/prd.md` |
| The backend and UI run locally. TACC is a batch model-serving backend. | `docs/tacc-notes.md`, ADR-0011 |

These are product facts, not a claim that every one is built. Section 9 records which are
implemented. Check it before a fact becomes a sentence in the UI.

Do not invent student counts, ratings, university partnerships, or outcome percentages.
This project has an evaluation, not a customer base. If a number is not in `docs/` or the
code, it does not exist.

## 3. Research base

Captured on 2026-11-13 with `web_fetch` and `agent-browser`. Full quotes and failures are
in `../../.agents/skills/web-copy/research/2026-11-13-web-copy-audit.md` in the course
workspace.

| Site | URL | What it is | Status |
|---|---|---|---|
| Khanmigo | https://www.khanmigo.ai/ | AI tutor for learners, teachers, districts | captured |
| Brilliant | https://brilliant.org/ | Interactive tutor for math and coding | captured |
| Tutor.com | https://www.tutor.com/ | Human tutoring service, B2B and B2C | captured |
| Yuanfudao | https://www.yuanfudao.com/ | Chinese online education company | captured, corporate homepage |
| Zuoyebang | https://www.zuoyebang.com/ | Chinese homework help company | captured, corporate homepage |

Failed on the marketing pass: Quizlet (403 captcha), Coursera homepage (JS shell), XuetangX
(JS shell), icourse163 (privacy modal only), Smart Education of China (JS shell).

### Marketing pages and product pages

The five captures above are marketing pages: they explain the product before the reader
uses it. They are the right evidence for the tagline and the auth panel, not for the
surfaces inside the app. Product pages were captured separately, because navigation,
practice, and progress use a different voice.

| Product page | URL | What it shows | Captured |
|---|---|---|---|
| Khan Academy, Algebra I unit | https://www.khanacademy.org/math/algebra-2018/quadratics?e=quadratic_equation&t=practice | Unit navigation, 29 skills, five progress states, quiz and unit test | 2026-11-13, `agent-browser` |
| Khan Academy, Parabolas intro | https://www.khanacademy.org/math/algebra-2018/quadratics/parabolas-intro-alg1/e/parabolas-intro | One problem, Skip and Check, Do 4 problems, Report a problem | 2026-11-13, `agent-browser` |
| Brilliant, Quadratics | https://brilliant.org/courses/quadratics/completing-the-square/?lesson=squaring-binomials | Level list, 80 lessons, 1468 exercises, Level Check | 2026-11-13, `agent-browser` |
| Coursera, asynchronous JavaScript | https://www.coursera.org/learn/packt-asynchronous-programming-in-javascript-complete-course-enzqd | 4 modules, "What you'll learn", "Skills you'll gain", Chinese product labels | 2026-11-13, `agent-browser` |

The AI tutor conversation itself was not captured. Khanmigo, Koji, and Coursera Coach put
the chat behind a sign-in on every public page; signing in is outside the research rules.
The chat rules below therefore come from this app's own surfaces and from the product-page
patterns, not from a captured tutor conversation.

### What the marketing pages do

- They speak to the reader as "you" and give the product a role: "your always-available
  teaching assistant" (Khanmigo), "Your personal tutor for math and coding" (Brilliant).
- They explain the mechanism as a sequence of actions: "asks guiding questions, sketches on
  your screen, and helps you work through each step" (Brilliant); "guides learners to find
  the answer themselves" (Khanmigo).
- They name the failure mode of the category and say the product avoids it: "without giving
  you direct answers" (Khanmigo), "not a cheating machine" (Brilliant).
- They prove with a unit and a method when they can: "4,000+ Expert Tutors in 250+ Subjects"
  (Tutor.com), "Data from 2025 post-session learner surveys" (Tutor.com).
- Chinese sites state scope as school stage plus subject ("小初高全科", "全学科") and name
  the audience in the block ("专为家长", "专为小学家长老师"). Their proof is a named
  benchmark ("微软 MSMarco 机器阅读理解排行榜，荣获全球第一").

### What the marketing pages do not do

- They do not lead with "AI". The AI tutors in the set do not use it as the main claim; the
  difference is what the product does with the course material.
- They do not use an outcome with no mechanism: "Online Tutoring That Accelerates Student
  Achievement" is the weak hero in the set.
- They do not stack superlatives: "Powerful insights, real results", "Unmatched tutor
  quality".
- They do not use exclamation marks or three-item feature lists in every block.
- They do not write institutional noun stacks: "Real-time data and actionable analytics to
  measure impact and continuously improve outcomes".

### What product pages do

- Labels carry the structure: "UNIT 16", "29 skills", "4 modules", "LEVEL 1". A label is
  usually a noun and a count, not a sentence.
- Progress is a legend of states, not a paragraph: "Mastered / Proficient / Familiar /
  Attempted / Not started".
- The action is an imperative: "Start Course challenge", "Do 4 problems", "Check", "Skip".
- Headings name what the reader gets: "What you'll learn", "Skills you'll gain",
  "Details to know", "Related content".
- Hierarchy is a breadcrumb: "Math > Algebra I (2018 edition) > Quadratics > Parabolas
  intro".
- A next step is one sentence and a link: "Not feeling ready for this? Check out Get ready
  for Algebra 1."
- A subtitle earns its place only with a fact the controls do not show: "4 modules",
  "5 hours to complete". It is not a restatement of the title.

The tagline belongs to the auth panel and the browser title. Do not repeat it as an in-app
page subtitle. Inside the app, a page title and a count do the work a tagline does on a
marketing page.

The two Chinese marketing captures are corporate homepages. Use them for register and proof
style, not for page structure. Their mission sentences are long and four-character heavy.
Do not imitate them. The Coursera product page, served in Chinese, is the better source for
Chinese product labels: "您将学到什么", "您将获得的技能", "4个模块", "第 1 单元", "单元详情".
Prefer those short labels to the corporate sentences.

## 4. Voice profile

| Dimension | What the captures do | Rule for this product |
|---|---|---|
| Address | Second person; the product is a named role | Use "you". The product is "the tutor" or "the assistant", one term per page. |
| Headline | Role plus scope, six to twelve words | Keep the tagline on the auth panel. Page titles are plain nouns: "Practice", "Knowledge base". |
| Mechanism | A sequence of concrete actions | Say: find course pages, quote the text, check it against the page, show the source. |
| Differentiation | Names the category failure | An answer without a page is not presented as verified. Say that once, plainly. |
| Proof | A number with a unit and a method | Use the citation check and, when results exist, the evaluation. Name what was measured. No invented counts. |
| Sentence length | Short declaratives, six to fourteen words | Six to sixteen words. One idea per sentence. |
| Verb register | ask, sketch, guide, work through, practice, check | find, quote, check, show, run, grade, open. |
| Concreteness | Named objects and tasks | "lecture page", "quoted text", "TACC job", "reference answer". |
| Promise strength | Hedged when the mechanism is limited | Say what the system does, not what it "ensures" or "guarantees". |
| Jargon | Student-facing terms, few internals | "source", "citation", "quoted text"; "work chain" only in instructor docs and internal notes. |
| Punctuation | Periods, rare colon, no exclamation | Periods. No exclamation marks, no emoji. |
| Section rhythm | Short heading, one to three sentences | One block, one idea. A section may be one line. |

Product pages add a second register. Use it for navigation, lists, and controls; use the
marketing register only where the reader is deciding whether to use the product.

| Dimension | Product pages | Rule for in-app surfaces |
|---|---|---|
| Structure | Label plus count | "29 skills", "4 modules", "80 lessons", "1468 exercises". |
| Progress | A legend of states | Show the states once, next to the list. Do not write a sentence per item. |
| Action | Imperative | "Start", "Check", "Skip", "Do 4 problems". One primary action per view. |
| Heading | What the reader gets | "What you'll learn", "Related content", "Unit details". |
| Hierarchy | Breadcrumb | "Math > Algebra I > Quadratics". Do not describe the path in prose. |
| Next step | One sentence plus a link | "Not feeling ready for this? Check out Get ready for Algebra 1." |
| Subtitle | A fact the controls do not show | "4 modules", "5 hours to complete". Otherwise omit. |

The existing tagline is the register to match on the auth panel: "Course-grounded answers
with evidence you can check." and "以课程材料为依据、引用可核查的答疑。" Do not use it as
an in-app page subtitle.

## 5. Where copy belongs

### 5.1 Five verdicts

Every text element gets one verdict before it gets a rewrite.

| Verdict | Use when | Examples |
|---|---|---|
| Copy required | A sentence the user needs to act, decide, or recover from a state. | Tagline, auth subtitle, code execution confirmation, destructive confirmation, error body, empty state with an action. |
| Label | A short name for a page, control, column, or state. | Page titles, tab names, table headers, status words. |
| Label plus icon | A label attached to a conventional icon, where the icon alone is ambiguous. | Sidebar navigation, file status, work-chain steps, source count. |
| Icon only | The action is conventional, reversible, and has an accessible name. | Copy, read aloud, retry, close, ellipsis, send, stop, pagination arrows, sidebar toggle. |
| No copy | The visual, the data, or the adjacent label already says it. | Page subtitles that restate the title, "AI summary", a provider badge on every answer, repeated preview notices. |

### 5.2 The test

Ask four questions in order:

1. Can the user act on this sentence? If no, it is probably not copy.
2. Does it name a page, a count, a rule, or a consequence? If no, it is atmosphere.
3. Does an icon already say it? If yes, delete the text or keep only the label.
4. Does the text say something the icon cannot? If yes, keep it.

### 5.3 Surface inventory

| Surface | Verdict | Current | Action |
|---|---|---|---|
| Auth left panel | Copy required | Three claims with icons | Keep the icons. Rewrite the three claims (section 8). |
| Auth field labels and placeholders | Label | "Email", "student@ust.hk" | Labels stay. Placeholders show an example, not an instruction. |
| Sidebar navigation | Label plus icon | Icon, label, tooltip | Keep. Never icon-only. The collapsed state uses the tooltip. |
| Top-bar page title | Label | Repeats the active nav label | Keep on pages without a visible heading, such as the knowledge grid. |
| Answer actions | Icon only | Copy, read aloud, retry | Keep. Accessible names are mandatory. |
| Source capsule | Label plus icon | Thumbnail stack and "2 course pages" | Keep the count. Drop the word "sources" if the thumbnails already say it. |
| Work-chain steps | Label plus icon | Status icon and step name | Keep the names. A status icon alone is ambiguous. |
| Model and tier badge | No copy | "deepseek · flash" on every answer | Remove. Put the model in the composer and the work-chain header. |
| Composer attach and mic | Icon only, or no copy | Paperclip, disabled mic, generic tooltip | Hide what does not work. A disabled icon with "Not available yet" is worse than no icon. |
| Thinking selector | Label plus icon | Trigger shows "Low" only | Render "Thinking: Low". |
| Chat suggestions | Copy required | Four course questions | Keep. They are the best onboarding copy on the page. |
| Evidence panel | Copy required | Page number, quoted text | Keep both. The image is the evidence. |
| Practice permanent alert | No copy | Alert above the tabs | Remove. Put one line under the disabled Generate button. |
| Practice tabs | Label | "Questions", "My solution" | Keep. |
| Code execution confirmation | Copy required | Title, body, two buttons | Keep. State the consequence and the scope. |
| Knowledge search | No copy | Icon and placeholder | No label needed. The placeholder is the instruction. |
| Knowledge tile menu | Icon only | Ellipsis | Keep. Accessible name "File actions". |
| File status | Label plus icon | Spinner and "Indexing" | Keep the label. A spinner alone does not say what is happening. |
| Knowledge subtitle | No copy | Defined but not rendered | Delete the key. |
| Builds permanent alert | No copy | Preview notice plus role rule | Remove. One read-only line or a disabled button. |
| Deadline table | Label | Headers and values | Keep. Table headers are copy. Do not abbreviate them. |
| Empty states | Copy required | One sentence | Keep. One sentence and one action. |
| Loading states | Copy required | "Loading" | Name the object: "Loading the knowledge base". |
| Error states | Copy required | Title, body, button | Keep. What happened, what to do. |
| Preview mode | Label | Badge plus repeated sentences | One badge in the top bar. Remove the repeated sentences. |
| Breadcrumb | Label | "All files / Lectures" | Navigation, not prose. |
| Pagination | Label plus icon | Arrows and "3 / 12" | Keep. |
| 403 and 404 | Copy required | Title, body, link | Keep. |
| Skip link | Copy required | "Skip to the main content" | Keep. |

## 6. Page rules

### 6.1 Global shell and states

- One Preview badge, in the top bar. No page repeats the preview sentence. "Preview: sample
  data." is the only preview text, and it sits next to the badge if a tooltip is needed.
- A page header has a title and at most one description sentence. The sentence says what
  the page does, not how it is built.
- Loading names the object. "Loading" alone is a placeholder, not copy.
- Error states say three things: what failed, what to do, what is preserved. "The answer
  stopped. Check the last step, or retry." No apology, no "Oops".
- Empty states say what will appear and how to make it appear, then offer one action.
- Destructive confirmations name the object, the scope, and the consequence. The confirm
  button repeats the verb: "Delete file", not "OK".
- Disabled controls do not get a paragraph. Put the reason in a tooltip or one line next to
  the control. If the reason is "not built", hide the control.

### 6.2 Auth

- The left panel sells the mechanism, not the model. Three claims maximum, each with a
  concrete noun.
- The form subtitle says what the account is for.
- The registration domain rule appears on the register page, not on login.
- Placeholders are examples. Labels carry the instruction.
- Field errors name the field and the fix.

### 6.3 Chat

- The empty state explains the mechanism in one sentence and offers four course-specific
  questions.
- The composer placeholder is an example question, not "Type here".
- The work chain uses user-facing step names. No tool names, no rule ids, no model ids in
  the collapsed view.
- A source shows a count and a page number. The page image is the evidence.
- No provider or tier badge on an answer. The model is a composer setting.
- An answer error names the failed step and offers retry.

### 6.4 Practice

- The subtitle states the two promises: a reference answer with sources, and code that runs
  as a TACC job.
- No permanent "not available" alert. Disable the action and say why once, next to it.
- The code confirmation states that the code runs under the course account and is not an
  isolated sandbox.
- Grading uses labels, not prose: score, verdict, explanation, reference answer, sources,
  test results.
- If the "My solution" tab is not available, hide it. Do not show a disabled tab with a
  roadmap sentence.

### 6.5 Knowledge base

- No page subtitle. The breadcrumb, the search field, and the grid carry the context.
- The search placeholder lists what is searchable: file name, folder, page text, summary.
- Use "Summary", not "AI summary". Keep the provenance line, for example "Summary by Qwen".
- Status is a verb plus an object: "Indexing", "Ready". Not a bare spinner.
- The student-facing empty state does not mention README commands or ingestion.
- Destructive copy names the index and the local copy, not "chunks".

### 6.6 Builds

- This is an instructor surface. Terse, factual, no sales voice.
- "Document", "Chunk limit", "Records", "State", "Timeline" are fine. "Shard" is not.
- In preview, one read-only line. Do not pair a preview notice with a role rule in the same
  alert.
- The empty state says what a build does, not how the queue is implemented.

### 6.7 Deadlines

- The table is the page. The subtitle states the rule in one sentence.
- Policy state labels must match the chat policy labels exactly.
- Fail-closed copy says what happens to the user, not "fails closed".
- Read-only copy says what is missing, not "P1".

## 7. Writing rules

### 7.1 English

1. Second person, present tense.
2. One idea per sentence, six to sixteen words.
3. Start with the verb or the object, not "We are excited to".
4. Name the page, the count, the rule, or the consequence.
5. Use "source" for a retrieved page. Use "citation" only when the quoted span has been
   verified.
6. Say "quoted text" to the reader. "Quoted span" is the internal term.
7. No exclamation marks, no emoji, no "AI-powered".
8. No triads. Two or four items are fine.
9. Errors: fact, next action, preserved state. No apology.
10. Buttons: verb plus object ("Run the code", "Delete file"). Never "OK".
11. Numbers: Arabic numerals, a unit, and a source when the number is a claim.
12. Do not promise what the code does not do. Check the claims ledger.

### 7.2 Chinese

1. 用"你"，不用"您"。
2. 动词开头，短句，一句话一个意思。
3. 术语固定，见 7.3。
4. 中英混排加半角空格：TACC 作业、Qwen 作业、6 位验证码。
5. 数字用阿拉伯数字：6 位、30 分钟、3/6 步。
6. 不写"赋能、助力、一站式、闭环、开启学习之旅"。
7. 不堆四字词。
8. 错误不说"抱歉"，说发生了什么、下一步做什么。
9. 按钮用"动词 + 对象"：运行代码、删除文件。不用"确定"。
10. 不逐字翻译英文。同一意图用中文产品说法。
11. 标点：中文用全角，英文和数字用半角。
12. 不用感叹号。

### 7.3 Terminology

| Concept | English | Chinese | Do not use |
|---|---|---|---|
| Retrieved page | source | 来源 | citation, reference, footnote |
| Verified span | citation | 引用 | source |
| Exact OCR text | quoted text | 引用原文 | quote, snippet |
| Ordered answer record | work chain, how this answer was built | 生成过程 | trace, chain of thought |
| Assignment policy state | policy state | 披露状态 | 策略状态 |
| Refuse to answer | abstain | 弃答 | refuse, reject |
| Answer shown after tests pass | reference answer | 参考答案 | standard answer |
| Knowledge generation run | build | 构建 | job, task |
| Dated assignment list | deadline registry | 作业登记表 | 截止日期表 |
| Instructor role | instructor | 教师 | 老师, 管理员 |
| Learner role | student | 学生 | 用户 |
| Batch job on TACC | TACC job | TACC 作业 | TACC 任务 |
| Sample-data mode | preview | 预览 | demo, 演示 |
| Page from the corpus | course page | 课件页 | 课程页 |

### 7.4 State patterns

| State | Shape | Example |
|---|---|---|
| Error | What failed. What to do. What is preserved. | "The answer stopped. Check the last step, or retry." |
| Empty | What will appear. How to make it appear. One action. | "No files here yet. Course documents appear after the instructor adds them." |
| Loading | "Loading" plus the object. | "Loading the knowledge base" |
| Confirmation | Question, consequence, scope, two buttons. | "Run this code on TACC? The code runs as a TACC job under the course account. It is not an isolated sandbox." |
| Destructive | Object, scope, consequence, verb button. | "Delete this file? This removes the file, its index, and the local copy." |
| Disabled | One reason, next to the control. | "Question generation is not connected in this build." |
| Count | Number plus unit, with a singular key for one item. | "{{count}} files" and "{{count}} file" |
| Time | Absolute date and time zone when it matters. | "Due 2026-11-20 23:59 HKT" |

### 7.5 Banned list

Structural: rule of three, "not just X, but Y", em dash chains, rhetorical-question openers,
bolded lead-in bullets, uniform paragraph length, emoji markers, exclamation marks, empty
intensifiers, invented proof.

English words to question: seamless, empower, unlock, elevate, supercharge, revolutionize,
cutting-edge, robust, leverage, holistic, curated, tailored, "designed to help you", "we
believe".

Chinese: 赋能、无缝、一站式、极致、打造、重新定义、颠覆、引领、助力、全方位、深度融合、
闭环、生态、抓手、颗粒度、心智、护城河、沉浸式、丝滑、开启你的…之旅、不仅…而且…、
为…保驾护航.

### 7.6 Review checklist

1. Can the user act on this sentence?
2. Does it name a page, a count, a rule, or a consequence?
3. Could it appear on any education site? If yes, make it specific to this course.
4. Does it claim something the code does not do? Check the ledger.
5. Is it a triad, a "not just X", a rhetorical question, or an em dash chain?
6. Does an icon already say it? Remove the text.
7. Does the text say something the icon cannot? Keep it.
8. Is the Chinese native, or a translation?
9. Are numbers and units consistent?
10. Do `en.ts` and `zh.ts` have the same keys?

## 8. Before and after

The suggested strings are a proposal for the next copy pass. They are not applied in this
change. Keys are in `src/verifiable_tutor/ui/web/src/lib/i18n/en.ts` and `zh.ts`.

### 8.1 Brand and auth

| Key | Now (EN / ZH) | Suggested (EN / ZH) | Why |
|---|---|---|---|
| `app.name` | Verifiable Tutor<br>可验证导师 | Keep for this release.<br>本次保留。 | The name is in the proposal, the page title, and every auth screen. A copy pass does not rename the product. If the name reopens, "可验证助教" names the role and "有据" is the short brand; see section 12. |
| `app.tagline` | Course-grounded answers with evidence you can check.<br>以课程材料为依据、引用可核查的答疑。 | Keep. Use it on the auth panel and in the browser title only. | It names the mechanism and the check. Do not repeat it inside the app. |
| `auth.loginSubtitle` | Use your course account to ask questions and review evidence.<br>使用课程账号提问并查看证据。 | Sign in with your course account to ask questions and check the sources.<br>用课程账号登录，提问并核对来源。 | "Review evidence" is vague. "Check the sources" is the action the UI supports. |
| `auth.domainHint` | Registration is limited to connect.ust.hk and ust.hk addresses.<br>仅限 connect.ust.hk 与 ust.hk 邮箱注册。 | Register with a connect.ust.hk or ust.hk address.<br>请使用 connect.ust.hk 或 ust.hk 邮箱注册。 | Move it to the register page. On login it answers a question the user does not have. |
| `auth.checks[0].title` | Every fact has a page<br>每个事实都有出处 | Answers name the page<br>答案标注页码 | "Every fact" is a guarantee the system cannot make. Name the behavior. |
| `auth.checks[0].body` | Answers cite the lecture or tutorial page, and the quoted span is checked against the page text.<br>答案标注出自讲义或教程的哪一页，并校验引用原文与页面文本一致。 | Each course claim points to a lecture or tutorial page, and the quoted text is compared with the page.<br>每条课程结论都指向讲义或教程的某一页，引用原文与页面文本逐字比对。 | "Span" is internal. "Compared" is the honest description of the check. |
| `auth.checks[1].title` | Practice is verified<br>练习经过验证 | Reference answers are verified<br>参考答案先验证 | Say what is verified, and when. |
| `auth.checks[1].body` | Reference answers compile and pass their tests before a question is shown.<br>参考答案先通过编译与测试，题目才会展示。 | A question appears only after its reference answer compiles and passes its tests.<br>参考答案编译并通过测试后，题目才会出现。 | The order is the promise. Put the condition first. |
| `auth.checks[2].title` | Policy is code<br>策略由代码执行 | Deadlines decide what is revealed<br>截止日期决定披露范围 | "Policy is code" speaks to engineers. Students need the consequence. |
| `auth.checks[2].body` | A dated deadline registry decides what the assistant may reveal, before the deadline and after it.<br>带日期的截止日期登记表在截止前后决定助手可以披露什么。 | Before a deadline the tutor gives hints, not full solutions. After it, it can explain the whole answer. The rule comes from the assignment registry.<br>截止前只给提示，不给完整解答；截止后可以完整讲解。规则来自作业登记表。 | State the behavior. The registry is the source, not the sentence. |
| `auth.sent` | Check your inbox for the next step.<br>请查收邮箱中的下一步。 | We sent a 6-digit code to your email.<br>6 位验证码已发送到你的邮箱。 | Say what was sent and where. |
| `auth.resetSubtitle` | We send a one-time link that stays valid for 30 minutes.<br>我们会发送一次性链接，30 分钟内有效。 | We will email a one-time link. It expires in 30 minutes.<br>我们会发送一次性链接，30 分钟内有效。 | Same fact, two sentences, easier to scan. |
| `auth.sixDigits` | Enter all six digits.<br>请输入全部六位数字。 | Enter all 6 digits.<br>请输入完整的 6 位验证码。 | Numerals match the rest of the UI. |

### 8.2 Common states

| Key | Now (EN / ZH) | Suggested (EN / ZH) | Why |
|---|---|---|---|
| `common.unavailable` | Not available yet<br>暂不可用 | Not available in this build.<br>此版本暂不可用。 | "Yet" promises a date. "Build" states the fact. |
| `common.previewNotice` | Preview build: this page uses sample data.<br>预览版本：本页使用示例数据。 | Preview: sample data.<br>预览：示例数据。 | The badge carries the sentence. The page does not need the full form. |
| `common.emptyTitle` | Nothing here yet<br>这里还没有内容 | Delete. Use a page-specific empty state. | A generic empty title is always less useful than the page's own. |
| `common.emptyBody` | There is no content for this view.<br>当前视图没有可显示的内容。 | Delete. Use a page-specific empty state. | "This view" is the implementation talking. |
| `common.errorTitle` | Something went wrong<br>出了点问题 | This page did not load<br>页面没有加载 | Name the failed object. "Something" is not a fact. |
| `common.errorBody` | The page could not load. Try again, or continue with another page.<br>页面无法加载。请重试，或前往其他页面。 | Reload the page, or open another one.<br>请刷新页面，或打开其他页面。 | Two actions, in the order a user tries them. |
| `common.serverError` | The backend returned an error. Try again.<br>后端返回了错误，请重试。 | The server returned an error. Try again in a moment.<br>服务器返回错误，请稍后重试。 | "Backend" is internal. "In a moment" sets an expectation. |
| `common.networkError` | Could not reach the backend. Check that it is running, then retry.<br>无法连接后端，请确认后端已启动后重试。 | Keep. | The local demo operator is the reader. It says exactly what to check. |

### 8.3 Chat

| Key | Now (EN / ZH) | Suggested (EN / ZH) | Why |
|---|---|---|---|
| `chat.emptyBody` | Answers cite the lecture or tutorial page they come from, and every citation opens the page image.<br>答案会标注出自讲义或教程的哪一页，点击引用可打开页面图。 | Each answer points to the lecture or tutorial page it uses. Open a source to see the page image and the quoted text.<br>每条回答都会标出所用的讲义或教程页。打开来源可查看页面图与引用原文。 | "Citation" means a verified span. The UI shows sources. Name what opens. |
| `chat.suggestionsTitle` | Try one of these<br>试试这些问题 | Start with one of these<br>从这些问题开始 | "Start" gives a next action. "Try" is a shrug. |
| `chat.composerPlaceholder` | Ask about a lecture, a tutorial, or an assignment concept<br>询问讲义、教程或作业中的概念 | Ask about a lecture, tutorial, or assignment concept<br>问讲义、教程或作业里的概念 | Trim the repeated article. The Chinese becomes a verb phrase. |
| `chat.thinking` (trigger) | The trigger shows only "Low".<br>触发器只显示"低"。 | Render "Thinking: Low".<br>显示"思考：低"。 | A bare level has no noun. The label already exists in the menu. |
| `chat.workChain` | Work chain<br>工作链 | How this answer was built<br>生成过程 | The panel is user-facing. "Work chain" is the glossary term for the team. |
| `chat.noWorkChainEvents` | No reasoning or tool calls were recorded for this answer.<br>本次回答没有记录思考或工具调用。 | Delete. Hide the panel when the chain is empty. | An empty panel plus an explanation is noise. |
| `chat.steps.understand` | Understand the question<br>理解问题 | Read the question<br>读题 | "Understand" claims a mental state. "Read" is the action. |
| `chat.steps.retrieve` | Retrieve course pages<br>检索课程页面 | Find course pages<br>查找课程页面 | "Retrieve" is information-retrieval jargon. |
| `chat.steps.verify` | Verify quoted spans<br>校验引用原文 | Check the quoted text<br>核对引用原文 | "Span" is internal. |
| `chat.steps.decide` | Apply the disclosure policy<br>应用披露策略 | Check the assignment rules<br>核对作业规则 | The student sees the rule, not the policy engine. |
| `chat.steps.cite` | Attach citations<br>附加引用 | Add the sources<br>附上来源 | The UI shows sources. Citations are earned by verification. |
| `chat.policyStates` | Pre-release / Active / Extension window / Post-deadline / Unknown<br>发布前 / 进行中 / 延期窗口 / 截止后 / 未知 | Not released / In progress / Extension / After the deadline / Not in the registry<br>未发布 / 进行中 / 延期 / 截止后 / 未登记 | "Unknown" hides the reason. "Not in the registry" explains the fail-closed behavior. |
| `chat.sourcesEmpty` | No sources for this answer<br>本轮回答没有引用来源 | No sources found<br>没有找到来源 | The answer may exist without sources. Say what was not found. |
| `chat.sourcesEmptyBody` | The retrieval step did not return a source for this turn.<br>检索没有返回可展示的来源。 | This answer did not find a course page it could cite.<br>这条回答没有找到可引用的课程页面。 | No "retrieval step", no "turn". |
| `chat.openSources` | Show this answer's citation sources<br>查看本轮引用来源 | Show the sources for this answer<br>查看这条回答的来源 | "Citation sources" doubles the term. "Turn" is internal. |
| `chat.evidenceEmpty` | Open a citation<br>打开一条引用 | Open a source<br>打开一条来源 | Match the noun the answer uses. |
| `chat.evidenceEmptyBody` | Select a citation in the answer to see the page image and the quoted span.<br>在答案中选择一条引用，查看页面图与引用原文。 | Choose a source in the answer to see the page image and the quoted text.<br>在答案中选择一条来源，查看页面图与引用原文。 | Same reason. |
| `chat.evidenceQuote` | Quoted span<br>引用原文 | Quoted text<br>引用原文 | "Span" is the internal term. The Chinese is already right. |
| `chat.errorBody` | The model did not finish this answer. Retry the same model, or check the work chain for the last step.<br>模型没有完成这次回答。可重试同一模型，或在工作链中查看最后一步。 | The model stopped before it finished. Check the last step, or retry.<br>模型没有写完这条回答。查看最后一步，或重试。 | The button is the retry. The sentence names the diagnosis path. |
| `chat.emptyCitation` | No citation selected<br>未选择引用 | No source selected<br>未选择来源 | Match the noun. |
| Answer footer badge | `{provider} · {tier}` on every answer, for example "deepseek · flash". | Remove. If provenance is needed, put the display name in the work-chain header. | Internal routing is not a user decision. |

### 8.4 Practice

| Key | Now (EN / ZH) | Suggested (EN / ZH) | Why |
|---|---|---|---|
| `practice.subtitle` | Generated questions carry a reference answer and citations. Code answers run in a TACC job.<br>生成的题目带参考答案与引用；代码答案在 TACC 作业中运行。 | Each question comes with a reference answer and its sources. Code answers run as a TACC job.<br>每道题附参考答案与出处；代码答案在 TACC 作业中运行。 | "Carry" is odd. "Sources" matches the UI. |
| `practice.unavailableTitle` and `practice.unavailableBody` | Practice execution is not available. The TACC execution job is pending. You can still review the question structure and the grading layout.<br>练习执行暂不可用。TACC 执行作业尚未实现。你仍可查看题目结构与评分版式。 | Delete the alert. Add one line under the disabled Generate button: "Question generation is not connected in this build."<br>删除提示条。在禁用按钮下加一行："此版本尚未接出题服务。" | The alert dominates the page before the user has done anything. |
| `practice.answerRequired` | Add an answer before you submit this question.<br>提交前请先填写答案。 | Write an answer first.<br>请先作答。 | Shorter. The button is already "Submit". |
| `practice.confirmationBody` | The code runs in a TACC job under the course account. It is not a hostile-user sandbox.<br>代码会在课程账号下的 TACC 作业中运行，不构成对抗性沙箱。 | The code runs as a TACC job under the course account. It is not an isolated sandbox.<br>代码以课程账号在 TACC 作业中运行，不是隔离沙箱。 | "Hostile-user" is a threat model. "Isolated" is the property the user needs. |
| `practice.solutionBody` | Paste a solution to receive a line-anchored explanation that respects the disclosure policy.<br>粘贴解答，获得逐行锚定且遵守披露策略的讲解。 | Paste a solution to get an explanation that points to each line.<br>粘贴解答，获得逐行对应的讲解。 | Drop the policy jargon. The policy is enforced, not advertised here. |
| `practice.solutionDisabled` | Line-anchored explanations arrive with the teaching package. This form shows the structure only.<br>逐行讲解随教学模块一起实现。此处仅展示结构。 | Solution explanations are not available in this build.<br>此版本暂不支持讲解自己的解答。 | Roadmap language is not a user state. |
| `practice.previewNotice` | Preview question. No answer is executed.<br>预览题目，不会执行任何答案。 | Delete. The top-bar Preview badge covers it. | A repeated preview sentence is noise. |

### 8.5 Knowledge base

| Key | Now (EN / ZH) | Suggested (EN / ZH) | Why |
|---|---|---|---|
| `knowledge.subtitle` | Every course document, its indexed text, and the Qwen summary.<br>本课程的全部文档、已索引文本与 Qwen 摘要。 | Delete. Not rendered. | A subtitle that restates the grid adds nothing. |
| `knowledge.uploadDisabled` | Uploads stay off until the TACC parse and embedding chain is verified end to end.<br>TACC 解析与向量化链路验收通过前，上传保持关闭。 | Hide the menu item. If a disabled item must stay: "Upload is not available in this build."<br>隐藏菜单项。若必须保留禁用项："此版本暂不支持上传。" | A student cannot act on the TACC chain. |
| `knowledge.emptyBody` | Run the ingestion command in the README to add the course PDFs.<br>按 README 运行入库命令即可加入课程 PDF。 | Course documents appear here after the instructor adds them.<br>教师入库课程文档后，文件会显示在这里。 | The student is not the operator. |
| `knowledge.summary` | AI summary<br>AI 摘要 | Summary<br>摘要 | Every summary here is generated. The label adds no information. |
| `knowledge.summaryMissing` | The summary has not been generated yet.<br>摘要尚未生成。 | No summary yet.<br>暂无摘要。 | Shorter. Same fact. |
| `knowledge.summaryModel` | Written by {{model}}<br>由 {{model}} 生成 | Summary by {{model}}<br>摘要由 {{model}} 生成 | The model wrote a summary, not the document. |
| `knowledge.deleteFileBody` | This removes the file, its chunks, and the local copy.<br>将删除该文件、它的分块以及本地副本。 | This removes the file, its index, and the local copy.<br>将删除文件、索引和本地副本。 | "Chunks" is an internal storage unit. |
| `knowledge.chatTitle` | About this page<br>关于这一页 | Page chat<br>本页问答 | The pane is a chat, not a page-info panel. A short label fits the collapsed rail and the mobile sheet. "关于" is translationese. |
| `knowledge.chatNotice` | Answers read the open page when they need it.<br>回答需要时会读取当前页面的正文。 | Delete the line. | The empty state and the composer already say what the pane reads. A permanent line above the thread adds noise. |
| `knowledge.chatEmpty` | Ask about the open file or page.<br>可以就当前文件或当前页提问。 | Ask about a term, a formula, or a line on this page.<br>可以问这一页上的术语、公式或某一行。 | Examples give the reader a first question; "file or page" repeats the title. |
| `knowledge.chatPlaceholder` | Ask about this page<br>就这一页提问 | Keep.<br>保留。 | With the title shortened to "Page chat", the placeholder carries the action and no longer repeats the title. |

### 8.6 Builds and deadlines

| Key | Now (EN / ZH) | Suggested (EN / ZH) | Why |
|---|---|---|---|
| `builds.subtitle` | Start one Qwen job per document shard, watch the states, and inspect the downloaded records.<br>每个文档分片提交一个 Qwen 作业，观察状态并检查下载的记录。 | Run one Qwen job per document, watch its state, and inspect the records it returns.<br>每个文档运行一个 Qwen 作业，查看状态并检查返回的记录。 | "Shard" is internal. The UI takes one document. |
| `builds.newBuildDescription` | Pick one document shard and the chunk limit. The build runs as one Qwen job.<br>选择一个文档分片和分片上限，构建会作为一个 Qwen 作业运行。 | Choose one document and a chunk limit. The build runs as one Qwen job.<br>选择一个文档和分块上限，构建会作为一个 Qwen 作业运行。 | Same reason. |
| `builds.previewNotice` and `builds.instructorOnly` | The alert title is the preview notice and the body is the role rule.<br>提示条标题是预览说明，正文是角色规则。 | One line: "Builds are read-only in this preview." Keep the role rule only when a non-instructor opens the page.<br>一行："预览中构建为只读。"角色规则只在非教师访问时显示。 | The current pairing answers two different questions in one alert. |
| `builds.emptyBody` | Start a build for one document shard to fill the knowledge base.<br>为一个文档分片启动构建，填充知识库。 | Start a build for a document to fill the knowledge base.<br>为文档启动构建，填充知识库。 | Same reason. |
| `builds.docId` | Document id<br>文档 id | Keep until a document picker exists. Then "Document".<br>保留到文档选择器出现，再改为"文档"。 | The field takes an id today. Do not label it as a picker before it is one. |
| `deadlines.subtitle` | The injected clock and the versioned registry decide what the assistant may reveal.<br>注入的时钟与版本化登记表决定助手可以披露什么。 | The registry and the current time decide what the assistant may reveal.<br>登记表与当前时间共同决定助手可以披露什么。 | "Injected clock" is a test seam. |
| `deadlines.readOnly` | Read-only view. The in-app editor is a P1 item.<br>只读视图，应用内编辑器属于 P1。 | Read-only. Editing the registry is not available yet.<br>只读。暂不支持在应用内编辑登记表。 | "P1" is backlog vocabulary. |
| `deadlines.failClosedTitle` | Unknown state fails closed<br>未知状态按最严格处理 | An unknown assignment blocks disclosure<br>未登记的作业默认不披露 | "Fails closed" is engineering vocabulary. State the behavior. |
| `deadlines.failClosedBody` | When an assignment is missing from the registry, the assistant abstains instead of guessing.<br>登记表中缺少某次作业时，助手会弃答而不是猜测。 | Keep. | "Abstains" is the glossary term, and the sentence explains it. |

## 9. Claims ledger

Every factual claim in the UI maps to a row here. A claim may ship only when the status is
"implemented", or when the surface is explicitly labeled Preview and the claim describes
the sample data. Otherwise, soften the claim to what the code does, or remove it.

| Claim | Where it appears | Backed by | Status |
|---|---|---|---|
| The quoted text is compared with the page. | Auth check 1, chat empty state | Span verifier | Not implemented (PRD G1) |
| Before a deadline the tutor gives hints; after it, full explanation. | Auth check 3 | Disclosure gate and deadline registry | Not implemented (PRD G2) |
| A reference answer compiles and passes tests before the question appears. | Auth check 2, practice subtitle | Practice generator | Not implemented (PRD G3) |
| A source opens the course page image. | Chat empty state, evidence panel | Corpus page image route | Implemented for corpus pages |
| An answer can read the open knowledge page. | Knowledge chat notice | Page-scoped retrieval in the agent loop | Implemented |
| Code runs as a TACC job under the course account. | Practice confirmation | `tacc/exec` | Not implemented; the run route returns 503 |
| Upload is closed until the parse and embedding chain is verified. | Knowledge upload item | Upload chain | Not implemented; hide the item |
| The work chain records each step. | Work-chain header | Persisted turn metadata | Implemented |

Where a status is "Not implemented", the suggested string in section 8 is the target for
the release that implements the feature, not copy to ship today. If the surface ships
before the feature, keep the current wording only while it is still true; otherwise move
the surface to preview.

## 10. Agent workflow

1. Name the surface and give it one verdict from section 5.1.
2. Check every factual claim against section 9.
3. If the surface is new, or the product's positioning changed, run the research again:
   three live captures, an evidence file, a voice profile.
4. Write the English in `en.ts`. Reuse an existing key when it fits. Add a key only when no
   key fits.
5. Write the Chinese in `zh.ts` for the same intent. Do not translate word for word.
6. Run `npx vitest run tests/i18n.test.tsx` and `npm run typecheck` from
   `src/verifiable_tutor/ui/web`.
7. Grep the draft for the banned patterns in section 7.5.
8. Compare the draft with the captured quotes. Rewrite any run of eight or more identical
   words.
9. Switch the language on every changed page. Check that no string overflows its control.
10. Commit the stage with the `git-commit` skill. Stage the files by path.

## 11. Verification

Run from `src/verifiable_tutor/ui/web`:

```bash
npx vitest run tests/i18n.test.tsx
npm run typecheck
```

Expected result on 2026-11-13:

- i18n parity: 2 tests passed.
- typecheck: no errors.

Manual checks:

- Every changed key exists in both files.
- No string ends with a period in a button or a badge.
- Every changed string fits its control at both languages and at 320 px width.
- No page repeats the preview sentence.

## 12. Open decisions

These are product decisions, not copy fixes. Record the decision before changing the
strings.

- Chinese product name: keep "可验证导师" for this release. It matches the English name and
  the proposal; a copy pass should not rename the product. If the name reopens, "可验证助教"
  names the role accurately and "有据" is the short brand. A rename touches the proposal,
  PRD, README, and page titles, so decide it before changing `zh.ts`.
- English role noun: "tutor" versus "assistant". The product name says Tutor. Pick one term
  per page and keep it.
- TACC in student copy: keep it only in the code execution confirmation, where it explains
  a real consequence. Drop it from empty states and settings.
- Qwen in student copy: keep it only as provenance ("Summary by Qwen"). Drop it from page
  subtitles.
- Provider and tier on answers: remove. If provenance is required, show the display name in
  the work-chain header, not on every answer.
- Icons: use the existing lucide set. No emoji, no decorative unicode.
