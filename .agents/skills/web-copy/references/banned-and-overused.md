# Banned and overused: the AI tells to remove

These are defaults to question, not absolute bans. A word that carries real meaning in a
technical sentence can stay; a word that is doing the work of an argument should go. The
test is always the same: if deleting it loses nothing, delete it.

## Structural tells (the bigger problem)

- **Rule of three.** Three adjectives, three features, three clauses in every sentence
  ("fast, reliable, and secure"). Real pages have uneven lists; a list of two or four is
  usually more honest.
- **"Not just X, but Y."** Also "more than a X — it's a Y". This construction is the single
  most common AI/marketing tell. Say the Y directly.
- **Em-dash chains.** One em dash is punctuation; three in a paragraph is a tic. Use a
  period.
- **Rhetorical-question openers.** "Ever wished you could…?", "What if…?" Ask a real
  question only if the page answers it.
- **Bolded lead-in bullets.** Every bullet opening with an **Adjective noun.** then a
  sentence. Write plain sentences.
- **Uniform paragraph length.** Four sentences in every block, every block the same shape.
  Vary it; let a section be one line.
- **Emoji section markers** and decorative unicode. None in this project.
- **Exclamation marks.** None in product copy; one at most in a celebration state, and only
  if the product already uses them.
- **Intensifiers with no content**: "truly", "really", " incredibly", "seamlessly",
  "effortlessly", "powerfully". Cut.
- **Invented proof.** "Thousands of students", "trusted by leading universities", "99%
  satisfaction" — if it is not in the project's documents, it does not exist.

## English vocabulary to question

seamless, seamlessly, empower, empowering, unlock, elevate, supercharge, revolutionize,
transform, cutting-edge, state-of-the-art, next-generation, robust, leverage, holistic,
end-to-end, best-in-class, world-class, game-changer, future-proof, frictionless,
effortless, delightful, curated, tailored, bespoke, "at the speed of thought", "built for
the future", "in today's fast-paced world", "whether you're a X or a Y", "designed to help
you", "we believe".

Most of these are fine in a sentence that makes a specific claim ("unlike a search box, the
answer cites the page it came from"). They are noise when they replace the claim.

## 中文高频 AI 腔

赋能、无缝、一站式、极致、打造、重新定义、颠覆、引领、助力、全方位、深度融合、闭环、
生态、抓手、颗粒度、心智、护城河、降本增效、数智化、沉浸式、丝滑、王炸、天花板、
"开启你的…之旅"、"让每一份努力都被看见"、"在这里，你可以…"、"无论你是…还是…"、
"不仅…而且…"、"为…保驾护航"、"重新定义学习体验"、"打造沉浸式学习闭环"。

替换原则：说出机制，不说口号。"以课程材料为依据、引用可核查的答疑" 胜过
"赋能高效学习"。

## 中文行文的具体毛病

- **"的"字堆叠**："这是一个基于课程的、可验证的、面向学生的答疑系统" → 拆句。
- **翻译腔**："你的学习之旅将在这里开启" → "从课程材料里找答案"。
- **四字词连用**：气势很足，信息为零。
- **全角形容词密度过高**：每句都有"高效、智能、便捷、全面"。
- **过度尊称**："您" 满篇。产品界面里 "你" 更自然，除非是正式通知。
- **中英混排未加空格**：中文与英文/数字之间留一个半角空格；这是项目现有文案的习惯。

## 自查清单（每条都要能回答"是"）

1. 每句是否有一个具体名词或动作？没有就重写。
2. 是否出现"不是…而是…"/"不仅…而且…"/三项排比？删掉一个。
3. 是否有无法在 `docs/` 或代码里找到出处的数字、评价、机构名？删掉。
4. 把这句话放到任意一个教育产品官网上，是否毫无违和？如果是，它还不够具体。
5. 中文是否像中文母语者写的产品文案，而不是英文的逐字翻译？
6. 是否引用了参考站点的原句？改写，不要照抄。

## 项目内已有好例子

- "Course-grounded answers with evidence you can check." — 名词具体，承诺可验证。
- "以课程材料为依据、引用可核查的答疑。" — 短句、动词开头、无形容词堆砌。
- "The backend is not reachable" / "无法连接后端" — 直接说事实，不卖萌。

新文案至少要达到这个密度：每句都有信息，没有一句是气氛。
