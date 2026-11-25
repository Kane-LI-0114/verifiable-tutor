<!-- ppt-master-schema: spec-lock/v1 -->
# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## communication
- primary_language: en
- audience: CSIT6000V instructor, TA, and classmates who judge a task-oriented system by its evidence.
- objective: Explain and demonstrate the verifiable study loop, then bound the claims with an honest evaluation.
- core_message: Verifiability is a system property: page-anchored retrieval, a span verifier, and policy as code make answers and practice checkable; the evaluation also shows where it fails.
- consumption_mode: presentation

## mode
- mode: custom
- mode_references: pyramid, briefing
- mode_behavior: Pyramid for the main argument: each page opens with a judgment and then shows one field of evidence; the three demo pages are proof turns; the closing page names the system property before the limits. Briefing restraint is used for architecture, data, and stack pages.

## visual_style
- visual_style: custom
- visual_style_references: editorial, swiss-minimal
- visual_style_behavior: Editorial column rules and running heads meet a Swiss twelve-column grid. Georgia display sits hard against the upper-left margin; Arial 16pt body sits on a strict baseline. No rounded cards, no shadows, no glass. Course pages and UI screenshots are full rectangular evidence plates. Cobalt marks the page edge, rules, markers, and key numbers only.

## colors
- background: #FAFAFA
- secondary_bg: #F4F4F5
- primary: #09090B
- accent: #1447E6
- secondary_accent: #52525B
- body_text: #18181B
- secondary_text: #52525B
- divider: #E4E4E7
- failure: #C10007
- surface: #FFFFFF
- grid: #E4E4E7

## typography
- font_family: Arial
- title_family: Georgia
- body_family: Arial
- code_family: Courier New
- body: 21.33
- title: 53.33
- cover_title: 85.33
- subtitle: 21.33
- annotation: 21.33
- code: 21.33

## icons
- library: tabler-outline
- stroke_width: 2
- inventory: tabler-outline/search, tabler-outline/file-text, tabler-outline/shield-check, tabler-outline/flask, tabler-outline/database, tabler-outline/cpu, tabler-outline/git-branch, tabler-outline/quote, tabler-outline/check, tabler-outline/x, tabler-outline/layers-intersect, tabler-outline/box, tabler-outline/gauge, tabler-outline/book, tabler-outline/arrow-right, tabler-outline/terminal-2, tabler-outline/alert-triangle, tabler-outline/clock, tabler-outline/route, tabler-outline/zoom-scan, tabler-outline/link, tabler-outline/message-chatbot, tabler-outline/list-check, tabler-outline/calendar-event, tabler-outline/lock, tabler-outline/eye, tabler-outline/scan, tabler-outline/bulb

## page_rhythm
- P01: anchor
- P02: dense
- P03: dense
- P04: dense
- P05: dense
- P06: dense
- P07: dense
- P08: dense
- P09: dense
- P10: breathing
- P11: dense
- P12: breathing
- P13: dense
- P14: dense
- P15: dense
- P16: dense
- P17: dense
- P18: anchor
- P19: dense
- P20: dense

## pptx_structure
- mode: flat

## forbidden
- `mask`, `<style>`, `class`, external CSS, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<set>`, `<script>` / event attributes, `<iframe>`
- HTML named entities in text; write typography as raw Unicode and escape XML reserved characters
- 英文正文字号控制在14-16，14最小了不能再小了；一个页面里也不要出现多个不同字号的文本 (user)
- 所有幻灯片文字、备注、demo UI 和模型回答必须英文 (user)
- Instructor/TA must only appear in conclusion future development and limitations (user)

## images
- p01_cover: images/ui-rag-source-pane.png | source=user | crop=no-crop
- p02_course: images/course-lecture2-p09.webp | source=user | crop=no-crop
- p07_workchain: images/ui-agent-workchain.png | source=user | crop=no-crop
- p08_p10: images/course-lecture2-p10.webp | source=user | crop=no-crop
- p08_p11: images/course-lecture2-p11.webp | source=user | crop=no-crop
- p09_sources: images/ui-rag-source-detail.png | source=user | crop=no-crop
- p11_chat: images/ui-knowledge-page9.png | source=user | crop=no-crop
- p12_after: images/ui-knowledge-page10-detail.png | source=user | crop=no-crop
- p15_practice: images/ui-practice-question.png | source=user | crop=no-crop
- p15_policy: images/ui-policy-refusal.png | source=user | crop=no-crop
- p17_tutorial: images/course-tutorial4-p40.webp | source=user | crop=no-crop
