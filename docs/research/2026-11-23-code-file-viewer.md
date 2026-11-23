# Read-only code and markdown viewer for the web UI

## Question

Which off-the-shelf front end viewer should the verifiable-tutor React 19 + Vite + TypeScript web UI use to display read-only course files (a C file of about 240 lines and a markdown README of about 170 lines) in a VS Code style pane with line numbers, and later highlight an anchored line range N..M the way PDF citations are anchored to a page?

Given constraints: the UI is built to static assets and served by the local FastAPI backend, with no CDN and no network at runtime; nothing is editable; the file count is small.

## Method

- Versions, publish dates, licenses and unpacked sizes come from npm registry JSON, for example https://registry.npmjs.org/monaco-editor, read on 2026-11-23.
- Weekly downloads come from https://api.npmjs.org/downloads/point/last-week/<package>, read on 2026-11-23.
- Repository state and issue activity come from the GitHub REST API, for example https://api.github.com/repos/microsoft/monaco-editor. The issue figures below are a sample of the 25 most recently updated issues per repository, pull requests excluded, read on 2026-11-23.
- Bundle sizes were measured on 2026-11-23 with esbuild 0.28.2 (esbuild --bundle --minify --format=esm --platform=browser --target=es2022), then gzip -9. One entry per candidate. React is external for React wrappers; monaco-editor is external for the Monaco wrapper. Workers and CSS are reported separately. Values are bytes of the minified bundle, before gzip, unless marked gz.
- No blog post or comparison site is used below.

## Comparison

| Candidate | Package(s) and latest version (publish date) | License | Gzipped size (measured) | React integration | C/C++ grammar | Line-range highlight | Markdown | Maintenance |
|---|---|---|---|---|---|---|---|---|
| Monaco Editor | monaco-editor 0.57.0 (2026-09-24); optional @monaco-editor/react 4.7.0 (2025-02-13) | MIT | 722 KB JS + 15 KB CSS + 95 KB worker; 1.18 MB JS with the default entry | Direct ESM import, or a wrapper whose default is a CDN | Monarch `c` and `cpp`, lazy loaded | createDecorationsCollection with isWholeLine | Monarch markdown tokenizer, no preview | Active; 14.3M downloads/week; 895 open issues |
| CodeMirror 6 | @codemirror/view 6.43.15 (2026-10-19), state 6.7.6 (2026-09-22), search 6.7.2 (2026-08-31), lang-cpp 6.0.3 (2025-06-19), lang-markdown 6.5.2 (2026-08-04), theme-one-dark 6.1.3 (2025-06-19); meta codemirror 6.0.2 (2025-06-19); optional @uiw/react-codemirror 4.25.12 (2026-09-24) | MIT | 208 KB full set; 68 KB without grammars | Plain class mounted in an effect; wrapper available | Lezer C++ parser via lang-cpp | Decoration.line in a StateField | Lezer CommonMark and GFM via lang-markdown | Active; 26.5M downloads/week for view; issue tracker moved off GitHub |
| Shiki | shiki 4.6.0, @shikijs/langs 4.6.0, @shikijs/themes 4.6.0, @shikijs/transformers 4.6.0 (all 2026-11-02) | MIT | 125 KB (core, JS engine, cpp, markdown, dark-plus) | Function returning an HTML string; call from an effect | TextMate cpp grammar | decorations option with start and end line | TextMate markdown grammar; rendering needs markdown-it | Active; 42.6M downloads/week; 116 open issues |
| highlight.js | highlight.js 11.12.0 (2026-08-12) | BSD-3-Clause | 12 KB (core, cpp, markdown) | Wrapper or dangerouslySetInnerHTML | JS grammar cpp | None built in | markdown grammar | Active; 57.7M downloads/week; 137 open issues |
| react-syntax-highlighter | react-syntax-highlighter 16.1.2 (2026-10-08); types from @types/react-syntax-highlighter 15.5.13 (2024-05-03) | MIT | 20 KB (PrismLight, cpp, markdown) | Component | Prism cpp via refractor | wrapLines plus lineProps | Prism markdown | Active; 9.9M downloads/week; 138 open issues |
| prism-react-renderer | prism-react-renderer 2.4.1 (2024-12-11) | MIT | 27 KB | Render prop component | Bundled Prism cpp | Tokens per line, style each line | Bundled Prism markdown | Stale: no release since 2024-12-11, repo last push 2025-01-02 |

Notes on the table.

- Sizes exclude React itself and exclude Monaco's workers unless stated. A local FastAPI server has no bandwidth problem, so the sizes matter for parse time, build configuration and install weight more than for transfer time.
- Line-range highlight means a documented API that styles whole lines by line number, not a CSS trick.
- The markdown column means syntax coloring of markdown source. None of these six renders markdown to HTML.
- License terms. MIT, which covers every candidate except highlight.js, grants use, copy, modification, distribution, sublicensing and sale provided the copyright and permission notice travels with copies or substantial portions, and disclaims warranty. BSD-3-Clause, which covers highlight.js, adds a clause that the names of the copyright holder and contributors may not be used to endorse derived products (https://github.com/highlightjs/highlight.js/blob/main/LICENSE, https://github.com/microsoft/monaco-editor/blob/main/LICENSE.txt).

## Monaco Editor

Packages and release. monaco-editor 0.57.0 was published on 2026-09-24 and @monaco-editor/react 4.7.0 on 2025-02-13, with 4.8.0-rc.3 published on 2025-11-21 (https://registry.npmjs.org/monaco-editor, https://registry.npmjs.org/@monaco-editor/react, https://github.com/suren-atoyan/monaco-react/releases). The repository has 47,000 stars, 895 open issues and a last push on 2026-11-21 (https://api.github.com/repos/microsoft/monaco-editor). The package downloaded 14,335,188 times in the last week (https://api.npmjs.org/downloads/point/last-week/monaco-editor). The unpacked package is 101,674,083 bytes in 1,918 files (https://registry.npmjs.org/monaco-editor).

License. MIT, copyright 2016 to present Microsoft Corporation. The text grants use, copy, modification, merge, publication, distribution, sublicensing and sale, on the condition that the copyright and permission notice are included in all copies or substantial portions, and provides the software as is without warranty (https://github.com/microsoft/monaco-editor/blob/main/LICENSE.txt).

Integration with Vite and React. The README says the ESM build is in /esm, that monaco.d.ts is the versioned API, and that the AMD build is deprecated (https://github.com/microsoft/monaco-editor/blob/main/README.md). Version 0.56.0 reorganized the ESM entry points: the changelog states that "custom bundles can now import monaco-editor/editor" and opt into features with monaco-editor/features/<feature>/register and language definitions with monaco-editor/languages/definitions/<language>/register (https://github.com/microsoft/monaco-editor/blob/main/CHANGELOG.md). That is the recipe that keeps a two-language viewer small.

```ts
// entry.ts, monaco-editor 0.57.0
import * as monaco from "monaco-editor/editor"
import "monaco-editor/features/find/register"
import "monaco-editor/languages/definitions/cpp/register"
import "monaco-editor/languages/definitions/markdown/register"
import EditorWorker from "monaco-editor/editor/editor.worker?worker"

self.MonacoEnvironment = { getWorker: () => new EditorWorker() }

export function mount(el: HTMLElement, text: string, language: "c" | "cpp" | "markdown") {
  return monaco.editor.create(el, {
    value: text, language, readOnly: true, lineNumbers: "on", theme: "vs-dark",
  })
}
```

The official ESM integration guide has a Vite section that asks the application to implement self.MonacoEnvironment.getWorker, because Vite has built-in support for web workers, and returns a worker per language label, defaulting to the editor worker (https://github.com/microsoft/monaco-editor/blob/main/docs/integrate-esm.md). The guide's sample still imports the full monaco-editor entry and uses deep specifiers such as monaco-editor/esm/vs/editor/editor.worker?worker. In 0.57.0 the published exports map is only "." plus "./*" mapped to ./esm/vs/*.js (https://unpkg.com/monaco-editor@0.57.0/package.json), so the deep specifier monaco-editor/esm/vs/editor/editor.worker does not resolve while monaco-editor/editor/editor.worker does; this was confirmed locally with esbuild 0.28.2, which honors the exports map.

@monaco-editor/react is a separate wrapper. Its README states that "by default, monaco files are being downloaded from CDN", that since v4.4.0 monaco-editor can be used as an npm package through loader.config({ monaco }), and it prints the Vite form of that setup with ?worker imports (https://github.com/suren-atoyan/monaco-react/blob/master/README.md). With no network at runtime, the CDN default must be replaced, and the wrapper adds 5,113 bytes gz over monaco-editor itself (measured).

Grammars. The C and C++ definitions are registered as two languages, c and cpp, both with a loader that dynamically imports ./cpp.js, and markdown is registered with the .md extensions and a loader for ./markdown.js (https://unpkg.com/monaco-editor@0.57.0/esm/vs/languages/definitions/cpp/register.js). The definition file for markdown exports conf and language with a Monarch tokenizer and no renderer (https://unpkg.com/monaco-editor@0.57.0/esm/vs/languages/definitions/markdown/markdown.js). Monaco does not use TextMate grammars; the README FAQ answers "Why doesn't the editor support TextMate grammars?" with a pointer to the separate monaco-tm project (https://github.com/microsoft/monaco-editor/blob/main/README.md). Syntax colors therefore come from Monarch rules, not from VS Code's TextMate themes.

Read-only, line numbers, line range, search.

- readOnly: the IStandaloneEditorConstructionOptions field is documented as "Should the editor be read only" and defaults to false, with a companion domReadOnly option (https://unpkg.com/monaco-editor@0.57.0/monaco.d.ts).
- Line numbers: lineNumbers accepts the LineNumbersType union of "on", "off", "relative", "interval", or a function (https://unpkg.com/monaco-editor@0.57.0/monaco.d.ts).
- Line range: editor.createDecorationsCollection(decorations) returns an IEditorDecorationsCollection, and each IModelDeltaDecoration has a range plus options with className and isWholeLine (https://unpkg.com/monaco-editor@0.57.0/monaco.d.ts). revealRangeInCenter scrolls a range into view.
- Search: the find widget is an editor action whose internal id is actions.find, listed in the same module as actions.findWithSelection and editor.actions.findWithArgs (https://unpkg.com/monaco-editor@0.57.0/esm/vs/editor/contrib/find/browser/findModel.js). When the opt-in entry is used, the find feature must be imported as monaco-editor/features/find/register.

```ts
const range = new monaco.Range(startLine, 1, endLine, 1)
editor.createDecorationsCollection([{ range, options: { isWholeLine: true, className: "citation-line" } }])
editor.revealRangeInCenter(range)
```

Theming. The built-in themes are "vs", "vs-dark", "hc-black" and "hc-light", typed as BuiltinTheme, and vs-dark is the VS Code dark default (https://unpkg.com/monaco-editor@0.57.0/monaco.d.ts).

Bundle, workers, tree-shaking, lazy loading. Measured: 2,812,659 bytes minified and 722,516 bytes gz for the opt-in entry with find, cpp and markdown, plus 96,554 bytes of CSS (14,989 gz); 704,177 bytes gz without the find feature, so find costs about 18 KB gz; 4,549,696 bytes minified and 1,179,315 bytes gz plus 27,193 bytes gz of CSS for the default monaco-editor entry; 307,278 bytes and 94,656 bytes gz for editor.worker.js. Language definitions are dynamic imports (2,049 bytes gz for cpp and 1,356 bytes gz for markdown in a split build), so grammars load on demand, but the editor core is a single large module graph and sets the floor at about 704 KB gz. @monaco-editor/react adds 5,113 bytes gz over monaco-editor. The package declares no sideEffects field (https://unpkg.com/monaco-editor@0.57.0/package.json).

Workers. A Vite build must ship the editor worker and hand it to Monaco through self.MonacoEnvironment.getWorker, as in the guide and the wrapper README cited above. The worker is a separate 95 KB gz asset served from the same origin, which suits a local static build, but it is the only candidate here that needs one.

Maintenance. 0.58.0-rc.2 was published on 2026-11-20, so releases continue, and the changelog is maintained (https://github.com/microsoft/monaco-editor/releases). In the sample of 25 recent issues, 8 were closed and 19 had comments (https://api.github.com/repos/microsoft/monaco-editor/issues?state=all&per_page=100&sort=updated).

## CodeMirror 6

Packages and release. The engine is a set of @codemirror packages: view 6.43.15 (2026-10-19), state 6.7.6 (2026-09-22), search 6.7.2 (2026-08-31), lang-cpp 6.0.3 (2025-06-19), lang-markdown 6.5.2 (2026-08-04) and theme-one-dark 6.1.3 (2025-06-19) (https://registry.npmjs.org/@codemirror/view, https://registry.npmjs.org/@codemirror/lang-cpp, https://registry.npmjs.org/@codemirror/lang-markdown). The codemirror package 6.0.2 (2025-06-19) is explicitly "an example configuration", not the engine (https://unpkg.com/codemirror@6.0.2/README.md). @uiw/react-codemirror 4.25.12 (2026-09-24) is a React wrapper with peer dependencies on codemirror, @codemirror/state and @codemirror/view (https://registry.npmjs.org/@uiw/react-codemirror). Downloads: 26,508,130 per week for view, 5,302,738 for lang-cpp (https://api.npmjs.org/downloads/point/last-week/@codemirror/view).

License. MIT for every package in the set (registry license fields above; for example https://unpkg.com/@codemirror/view@6.43.15/package.json).

Integration with Vite and React. Install the individual packages and mount an EditorView in an effect. There is no worker, no wasm asset and no CDN fetch; the library is plain ES modules that the bundler includes. The system guide describes the package set as modular, with each package published separately (https://codemirror.net/docs/guide/#modularity).

```ts
import { EditorState } from "@codemirror/state"
import { EditorView, keymap, lineNumbers } from "@codemirror/view"
import { cpp } from "@codemirror/lang-cpp"
import { markdown } from "@codemirror/lang-markdown"
import { search, searchKeymap } from "@codemirror/search"
import { oneDark } from "@codemirror/theme-one-dark"

const view = new EditorView({
  parent: el,
  state: EditorState.create({
    doc: text,
    extensions: [
      lineNumbers(),
      EditorState.readOnly.of(true),
      EditorView.editable.of(false),
      search(),
      keymap.of(searchKeymap),
      kind === "markdown" ? markdown() : cpp(),
      oneDark,
    ],
  }),
})
```

Grammars. lang-cpp is a Lezer C++ parser exposed as cppLanguage with a cpp() support function (https://unpkg.com/@codemirror/lang-cpp@6.0.3/dist/index.d.ts). lang-markdown provides commonmarkLanguage for strict CommonMark and markdownLanguage for GFM plus subscript, superscript and emoji, and it depends on @codemirror/lang-html for embedded HTML (https://unpkg.com/@codemirror/lang-markdown@6.5.2/dist/index.d.ts, https://registry.npmjs.org/@codemirror/lang-markdown).

Read-only, line numbers, line range, search.

- Read-only: EditorState.readOnly is a facet whose value the readOnly getter returns, "consulted by commands and extensions that implement editing functionality", defaulting to false (https://codemirror.net/docs/ref/#state.EditorState^readOnly). EditorView.editable is a separate facet that controls the contenteditable attribute (https://codemirror.net/docs/ref/#view.EditorView^editable).
- Line numbers: the lineNumbers() extension draws a gutter with line numbers (https://codemirror.net/docs/ref/#view.lineNumbers).
- Line range: Decoration.line(spec) creates a line decoration whose spec accepts a class or DOM attributes (https://unpkg.com/@codemirror/view@6.43.15/dist/index.d.ts), and decorations are supplied through EditorView.decorations; the decoration example on the site shows the StateField pattern (https://codemirror.net/examples/decoration/).
- Search: the search() extension, searchKeymap, openSearchPanel, findNext, findPrevious, getSearchQuery and setSearchQuery are all exported by @codemirror/search (https://unpkg.com/@codemirror/search@6.7.2/dist/index.d.ts), which is the only built-in find UI among the lighter candidates here.

Theming. The dark theme package this note proposes is @codemirror/theme-one-dark, which its README describes as "the One Dark theme" (https://code.haverbeke.berlin/codemirror/theme-one-dark). That is One Dark, not VS Code Dark+; matching VS Code requires an application theme written with EditorView.theme and a HighlightStyle, both public API.

Bundle, workers, tree-shaking. Measured: 610,163 bytes minified and 207,855 bytes gz for view, state, search, cpp, markdown and oneDark together; 209,616 bytes and 67,648 bytes gz for view, state and lineNumbers alone; the cpp grammar adds about 55 KB gz, markdown about 98 KB gz, search about 5 KB gz and oneDark about 11 KB gz. @uiw/react-codemirror with its basic setup measures 398,243 bytes and 129,212 bytes gz with React external. All packages declare "sideEffects": false (for example https://unpkg.com/@codemirror/view@6.43.15/package.json). No worker and no wasm. There is no internal lazy loading: grammars are ordinary modules that the bundler includes, so code splitting is the application's choice through a dynamic import of the viewer component.

Maintenance. The project moved its development and issue tracker off GitHub: codemirror.net links "Code" and "Report an Issue" to code.haverbeke.berlin (https://codemirror.net/), and the GitHub repository codemirror/dev is archived with a last push on 2026-04-15 (https://api.github.com/repos/codemirror/dev). Releases arrive per package, several in 2026. Response times on the new tracker were not measured, so "issues are answered" is unconfirmed for this project.

## Shiki

Packages and release. shiki 4.6.0, @shikijs/langs 4.6.0, @shikijs/themes 4.6.0 and @shikijs/transformers 4.6.0 were all published on 2026-11-02 (https://registry.npmjs.org/shiki, https://registry.npmjs.org/@shikijs/transformers). The package downloaded 42,649,146 times in the last week (https://api.npmjs.org/downloads/point/last-week/shiki). The repository has 13,949 stars, 116 open issues and a last push on 2026-11-02 (https://api.github.com/repos/shikijs/shiki).

License. MIT (registry license field; the documentation footer reads "Released under the MIT License", https://shiki.style/guide/).

Integration with Vite and React. Shiki turns a string into an HTML string or a token tree, so React mounts the result rather than an editor instance. The fine-grained bundle is the documented way to keep it small for a web app: shiki/core "does not include any themes or languages or the wasm binary", and themes and languages are imported one by one (https://shiki.style/guide/bundles). The JavaScript RegExp engine avoids the Oniguruma wasm file; the docs say its advantage "is that it doesn't require loading a large WebAssembly file" and that as of Shiki 3.9.1 all built-in languages are supported (https://shiki.style/guide/regex-engines). That removes the last network and binary asset concern for the offline build.

```ts
import { createHighlighterCore } from "shiki/core"
import { createJavaScriptRegexEngine } from "shiki/engine/javascript"
import cpp from "@shikijs/langs/cpp"
import markdown from "@shikijs/langs/markdown"
import darkPlus from "@shikijs/themes/dark-plus"
import { transformerRenderLineNumber } from "@shikijs/transformers"

const highlighter = await createHighlighterCore({
  themes: [darkPlus],
  langs: [cpp, markdown],
  engine: createJavaScriptRegexEngine(),
})

const html = highlighter.codeToHtml(text, {
  lang: "cpp",
  theme: "dark-plus",
  transformers: [transformerRenderLineNumber()],
  decorations: [{
    start: { line: start - 1, character: 0 },
    end: { line: end - 1, character: -1 },
    properties: { class: "citation-line" },
  }],
})
```

Grammars. Shiki uses TextMate grammars, the same grammar format VS Code uses (https://shiki.style/guide/regex-engines). The cpp grammar pulls its dependencies in automatically; a local check loaded regexp, c, glsl, cpp-macro and cpp. Markdown is a grammar too, so Shiki colors markdown source; rendering markdown to HTML needs a separate renderer, and Shiki ships an official markdown-it plugin for code blocks inside rendered markdown (https://shiki.style/packages/markdown-it).

Read-only, line numbers, line range, search.

- Read-only: there is no editing surface at all. The output is HTML that the browser renders.
- Line numbers: @shikijs/transformers 4.6.0 exports transformerRenderLineNumber, documented in its type declarations as "Render line number as separate tokens", with options including classLineNumber and start (https://unpkg.com/@shikijs/transformers@4.6.0/dist/index.d.mts).
- Line range: codeToHtml accepts a decorations array whose items take start and end positions of line and character, 0-indexed, plus properties such as class (https://shiki.style/guide/decorations). A negative character counts from the end of the line, so character -1 covers a whole line.
- Search: none. The documented surface is codeToHtml, codeToTokens and codeToHast plus transformers and decorations (https://shiki.style/guide/install, https://shiki.style/guide/decorations); no in-document search is documented. Browser find works on the rendered text, and an application level search can be built by re-rendering with a decoration per match, but the viewer must supply it.

Theming. @shikijs/themes exports ./dark-plus, and the theme module's first line is "Theme: dark-plus" with editor.background #1E1E1E and editor.foreground #D4D4D4, the VS Code Dark+ palette (https://unpkg.com/@shikijs/themes@4.6.0/dist/dark-plus.mjs). The themes page notes that themes are redistributed from tm-themes and carry their own permissive licenses (https://shiki.style/themes).

Bundle, workers, tree-shaking. Measured: 1,103,851 bytes minified and 125,459 bytes gz for core, the JS engine, cpp, markdown and dark-plus; with code splitting the cpp grammar is 2,049 bytes gz and markdown 1,356 bytes gz on demand. No worker is required. The package declares "sideEffects": false (https://unpkg.com/shiki@4.6.0/package.json). Highlighting is async on first use, so lazy loading means a dynamic import of the highlighter plus a loading state.

Maintenance. 4.6.0 shipped on 2026-11-02, 4.5.0 on 2026-10-01 and 4.4.3 on 2026-08-10 (https://github.com/shikijs/shiki/releases). In the sample of 25 recent issues, 14 were closed and 8 had comments (https://api.github.com/repos/shikijs/shiki/issues?state=all&per_page=100&sort=updated).

## highlight.js

Package and release. highlight.js 11.12.0, published 2026-08-12, 57,744,106 downloads in the last week (https://registry.npmjs.org/highlight.js, https://api.npmjs.org/downloads/point/last-week/highlight.js). Repository: 25,018 stars, 137 open issues, last push 2026-11-11 (https://api.github.com/repos/highlightjs/highlight.js).

License. BSD 3-Clause, copyright 2006 Ivan Sagalaev, with the three standard clauses: source redistribution must keep the copyright notice and disclaimer, binary redistribution must reproduce them in the documentation, and the names of the copyright holder and contributors may not be used to endorse derived products (https://github.com/highlightjs/highlight.js/blob/main/LICENSE).

Integration. npm install highlight.js, import the core plus the two languages, register them, and call highlight(code, { language }). The README documents the browser and Node usage and the registerLanguage pattern (https://github.com/highlightjs/highlight.js/blob/main/README.md). There is no React component: the returned string must be set with dangerouslySetInnerHTML, or wrapped by react-syntax-highlighter.

Grammars. C and C++ come from src/languages/cpp.js and markdown from src/languages/markdown.js (published as lib/languages/...), both plain JS grammar functions registered by name (https://github.com/highlightjs/highlight.js/tree/main/src/languages).

Read-only, line numbers, line range, search. It is a highlighter, not a viewer: read-only needs no configuration, but the documented API returns one HTML string for the whole block, with no line numbering, no per-line hook and no search (https://highlightjs.org/usage/). Line numbers must be added by the application or by a wrapper.

Theming. The package ships CSS themes, including vs.css, vs-dark.css and vs2015.css, which are the VS Code palettes (https://github.com/highlightjs/highlight.js/tree/main/src/styles).

Bundle and tree-shaking. Measured: 29,521 bytes minified and 11,634 bytes gz for core, cpp and markdown. Registering only the needed grammars is the documented custom build path, grammars are separate modules so unregistered languages are not bundled, and the package marks CSS files as side effects (https://unpkg.com/highlight.js@11.12.0/package.json). No worker, no wasm.

Maintenance. 11.12.0 on 2026-08-12 and 11.11.2 on 2026-06-23 (https://github.com/highlightjs/highlight.js/releases); 7 of 25 recent issues closed and 13 with comments (https://api.github.com/repos/highlightjs/highlight.js/issues?state=all&per_page=100&sort=updated).

## react-syntax-highlighter

Package and release. react-syntax-highlighter 16.1.2, published 2026-10-08, 9,922,874 downloads in the last week (https://registry.npmjs.org/react-syntax-highlighter, https://api.npmjs.org/downloads/point/last-week/react-syntax-highlighter). Repository: 4,675 stars, 138 open issues, last push 2026-10-08 (https://api.github.com/repos/react-syntax-highlighter/react-syntax-highlighter).

License. MIT, copyright 2019 Conor Hastings (https://github.com/react-syntax-highlighter/react-syntax-highlighter/blob/master/LICENSE).

Integration. Install the package and the language modules, then register them on the light build. The README documents PrismLight and registerLanguage, and the two builds (Prism and lowlight/highlight.js) (https://github.com/react-syntax-highlighter/react-syntax-highlighter/blob/master/README.md). TypeScript needs @types/react-syntax-highlighter, because the package has no types field; the types package is at 15.5.13, published 2024-05-03, one major version behind the 16.x runtime (https://registry.npmjs.org/react-syntax-highlighter, https://registry.npmjs.org/@types/react-syntax-highlighter).

```tsx
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter"
import cpp from "react-syntax-highlighter/dist/esm/languages/prism/cpp"
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown"

SyntaxHighlighter.registerLanguage("cpp", cpp)
SyntaxHighlighter.registerLanguage("markdown", markdown)
```

Line numbers and line range. showLineNumbers draws a gutter, showInlineLineNumbers puts the number inside each line, and startingLineNumber sets the first number. wrapLines wraps each line in an element, and lineProps accepts a function that receives the line number and returns props for that line, which is the supported way to mark a range (https://github.com/react-syntax-highlighter/react-syntax-highlighter/blob/master/README.md). There is no search.

Grammars. Prism grammars for cpp and markdown from refractor, registered by name, so both languages are available (https://registry.npmjs.org/react-syntax-highlighter).

Theming. The package ships Prism and highlight.js style objects and CSS, so a VS Code-like palette is a style import away, but there is no built-in theme switcher.

Bundle. Measured: 59,760 bytes minified and 20,022 bytes gz for PrismLight with cpp and markdown, React external. The package depends on prismjs, lowlight, refractor, highlight.js and @babel/runtime, so the install is larger than the bundle (https://registry.npmjs.org/react-syntax-highlighter). Language modules are separate files, so a bundler splits them only if the import is dynamic.

Maintenance. 16.1.2 on 2026-10-08 and 16.1.1 on 2026-02-26 (https://github.com/react-syntax-highlighter/react-syntax-highlighter/releases); 9 of 25 recent issues closed and 23 with comments (https://api.github.com/repos/react-syntax-highlighter/react-syntax-highlighter/issues?state=all&per_page=100&sort=updated).

## prism-react-renderer

Package and release. prism-react-renderer 2.4.1, published 2024-12-11, 8,088,000 downloads in the last week (https://registry.npmjs.org/prism-react-renderer, https://api.npmjs.org/downloads/point/last-week/prism-react-renderer). Repository: 2,000 stars, 13 open issues, last push 2025-01-02 (https://api.github.com/repos/FormidableLabs/prism-react-renderer).

License. MIT, copyright 2018 Nearform (https://github.com/FormidableLabs/prism-react-renderer/blob/master/LICENSE).

Integration. npm install prism-react-renderer, then render the Highlight component with code, language and theme, using the render prop's tokens, getLineProps and getTokenProps (https://github.com/FormidableLabs/prism-react-renderer/blob/master/README.md). It has a peer dependency on react and ships its own customized Prism that does not touch the global namespace.

Grammars. It bundles "a couple of common language syntaxes"; a local check confirmed that Prism.languages.cpp and Prism.languages.markdown are present and tokenize correctly (https://github.com/FormidableLabs/prism-react-renderer/blob/master/README.md). Adding an unlisted language uses the prism prop escape hatch with a full Prism instance.

Line numbers and line range. The render prop receives tokens grouped per line, so the application maps each line to an element and can add its own gutter and line class; there is no built-in numbering, no search, and no range API. The README documents getLineProps for per-line props (https://github.com/FormidableLabs/prism-react-renderer/blob/master/README.md).

Theming. The package "comes with its own VSCode-like theming format" and a themes object that includes vsDark and vsLight (https://github.com/FormidableLabs/prism-react-renderer/blob/master/README.md). A local check listed 18 built-in themes.

Bundle. Measured: 86,230 bytes minified and 26,556 bytes gz with React external. The package declares "sideEffects": true, which limits tree-shaking (https://unpkg.com/prism-react-renderer@2.4.1/package.json).

Maintenance. No release since 2.4.1 on 2024-12-11 and no push since 2025-01-02, although the README still labels the project "Active" (https://github.com/FormidableLabs/prism-react-renderer/releases, https://github.com/FormidableLabs/prism-react-renderer/blob/master/README.md#maintenance-status). 18 of 25 recent issues are closed and 21 have comments, so issues still get attention (https://api.github.com/repos/FormidableLabs/prism-react-renderer/issues?state=all&per_page=100&sort=updated). For a two year old release this is the weakest maintenance signal among the six.

## Candidates that were not kept

- vite-plugin-monaco-editor 1.1.0 was published on 2022-07-02 and has had no release since, so it is not a maintained integration path and should not be used (https://registry.npmjs.org/vite-plugin-monaco-editor).
- prismjs 1.30.0 (2025-03-10) is the highlighting engine underneath the React wrappers, not a React viewer; it is only relevant through react-syntax-highlighter or prism-react-renderer (https://registry.npmjs.org/prismjs).
- @uiw/react-codemirror and @monaco-editor/react are React wrappers over CodeMirror 6 and Monaco, not separate engines; they are treated inside those two sections.

## Tradeoffs for this app

Offline, no CDN. Monaco is the only candidate whose default path reaches the network: @monaco-editor/react downloads monaco from a CDN unless loader.config({ monaco }) is called, and Monaco needs a worker asset served from the same origin. Shiki with the JavaScript engine needs neither a worker nor wasm, and CodeMirror needs neither. For a build that is served by FastAPI with no network, Shiki and CodeMirror remove a class of runtime failure rather than configuring around it.

Small file count. Two files of 240 and 170 lines do not need virtualization, incremental parsing or an editor's undo stack. Shiki's static HTML and CodeMirror's viewport rendering are both far below any size where a single document would be slow. Monaco's extra machinery buys features this screen does not use, except the find widget.

Citations anchored to line ranges. All six can mark a range, but the shape differs. Monaco and CodeMirror keep a live document and decorations that must be updated when the editor state changes; Shiki recomputes the HTML from the source text and the stored range on each render, so the citation state is the source of truth and the render is a pure function of it. That matches how a stored citation (file, start line, end line) should behave, and it avoids a class of stale decoration bugs. Line numbering must be converted consistently: Shiki's decorations are 0-indexed while stored citations are naturally 1-indexed, and CodeMirror and Monaco take line numbers as 1-indexed positions.

Search. Only Monaco and CodeMirror ship a find UI. Shiki and the three highlighters do not, so in-document search would rely on browser find or on an application search that re-renders matches. For a 240 line file this is a small gap, but it is the one requirement Shiki does not meet out of the box.

Markdown files with relative links and images. None of these viewers renders markdown, so none resolves a relative ![image](img/x.png) or [link](notes.md) on its own; all of them show the source text and color it. If the product wants a rendered README, that is a separate markdown renderer whose output needs URL rewriting to backend routes, and in that case the line numbers and the line-range citation apply to the source view, not the rendered one. Keeping markdown as a source view avoids the rewriting problem entirely and keeps one citation model for both file types.

Theme fidelity. Monaco's vs-dark is VS Code's own editor, but its token colors come from Monarch rules, not from VS Code's TextMate themes. Shiki's dark-plus is the VS Code Dark+ TextMate theme applied to the same TextMate grammars VS Code uses, so the colors match VS Code more exactly than Monaco's do for the same grammar. CodeMirror's dark theme package here is One Dark, not VS Code Dark+, so a VS Code look is a hand-written theme.

Bundle and build complexity. Measured gz for the same two languages: 125 KB for Shiki, 208 KB for CodeMirror, 722 KB plus a 95 KB worker and 15 KB of CSS for Monaco. The Monaco number excludes the wrapper and assumes the 0.56+ opt-in entry points; the default entry is 1.18 MB gz. On localhost the transfer cost is irrelevant, but the worker wiring and the entry point churn are real build work, and the 0.57.0 exports map already breaks the deep worker specifier printed in the official sample.

Maintenance. Shiki, Monaco and CodeMirror are all actively released in 2026. prism-react-renderer has not released since 2024-12-11. @monaco-editor/react has had no stable release since 2025-02-13; only release candidates in 2025. @types/react-syntax-highlighter is a major version behind its runtime.

What the repository already contains. The web app already depends on shiki ^4.6.0 (src/verifiable_tutor/ui/web/package.json) and already has a lazily loaded, offline Shiki setup in src/verifiable_tutor/ui/web/src/lib/highlighter.tsx: createHighlighterCore with createJavaScriptRegexEngine, per-language dynamic imports, github-light and github-dark themes, and a token-to-React-node renderer. C and C++ are not in its language map, and its themes are GitHub's, not VS Code's. Choosing Shiki therefore means adding shiki/langs/cpp.mjs and a VS Code theme to a module that already works, while Monaco or CodeMirror would add a second highlighting stack and a second theme system next to it.

## Recommendation

Primary choice: Shiki 4.6.0 with the fine-grained bundle (shiki/core, createJavaScriptRegexEngine, @shikijs/langs/cpp, @shikijs/langs/markdown, @shikijs/themes/dark-plus, @shikijs/transformers transformerRenderLineNumber), rendered into a scroll container that the app owns. It is read-only by construction, it reproduces VS Code's Dark+ colors from VS Code's own TextMate theme and grammars, it needs no worker, no CDN and no wasm, its gzipped cost is the lowest of the three real viewers at 125 KB, and its decorations option maps a stored line range to a highlight in one pure render.

Fallback: CodeMirror 6 (@codemirror/state, view, search, lang-cpp, lang-markdown and a hand-written VS Code-like theme). It keeps the no-worker, no-CDN property, adds a first-party find panel, read-only facets and line decorations for about 208 KB gz, and gives up only the exact VS Code palette. If in-document search with match navigation becomes a hard requirement, CodeMirror should become the primary choice.

## Sources

All URLs were read on 2026-11-23.

Registry metadata and download counts
- https://registry.npmjs.org/monaco-editor
- https://registry.npmjs.org/@monaco-editor/react
- https://registry.npmjs.org/codemirror
- https://registry.npmjs.org/@codemirror/view
- https://registry.npmjs.org/@codemirror/state
- https://registry.npmjs.org/@codemirror/search
- https://registry.npmjs.org/@codemirror/lang-cpp
- https://registry.npmjs.org/@codemirror/lang-markdown
- https://registry.npmjs.org/@codemirror/theme-one-dark
- https://registry.npmjs.org/@uiw/react-codemirror
- https://registry.npmjs.org/shiki
- https://registry.npmjs.org/@shikijs/transformers
- https://registry.npmjs.org/@shikijs/langs
- https://registry.npmjs.org/@shikijs/themes
- https://registry.npmjs.org/highlight.js
- https://registry.npmjs.org/react-syntax-highlighter
- https://registry.npmjs.org/@types/react-syntax-highlighter
- https://registry.npmjs.org/prism-react-renderer
- https://registry.npmjs.org/prismjs
- https://registry.npmjs.org/vite-plugin-monaco-editor
- https://api.npmjs.org/downloads/point/last-week/monaco-editor (and the same endpoint for each package above)
- https://unpkg.com/monaco-editor@0.57.0/package.json
- https://unpkg.com/monaco-editor@0.57.0/monaco.d.ts
- https://unpkg.com/@codemirror/view@6.43.15/dist/index.d.ts
- https://unpkg.com/@codemirror/search@6.7.2/dist/index.d.ts
- https://unpkg.com/@codemirror/lang-cpp@6.0.3/dist/index.d.ts
- https://unpkg.com/@codemirror/lang-markdown@6.5.2/dist/index.d.ts
- https://unpkg.com/@shikijs/transformers@4.6.0/dist/index.d.mts
- https://unpkg.com/@shikijs/themes@4.6.0/dist/dark-plus.mjs
- https://unpkg.com/shiki@4.6.0/package.json
- https://unpkg.com/highlight.js@11.12.0/package.json
- https://unpkg.com/prism-react-renderer@2.4.1/package.json
- https://unpkg.com/codemirror@6.0.2/README.md

Project repositories and licenses
- https://github.com/microsoft/monaco-editor
- https://github.com/microsoft/monaco-editor/blob/main/README.md
- https://github.com/microsoft/monaco-editor/blob/main/LICENSE.txt
- https://github.com/microsoft/monaco-editor/blob/main/CHANGELOG.md
- https://github.com/microsoft/monaco-editor/blob/main/docs/integrate-esm.md
- https://github.com/microsoft/monaco-editor/releases
- https://github.com/suren-atoyan/monaco-react/blob/master/README.md
- https://github.com/suren-atoyan/monaco-react/releases
- https://github.com/codemirror/dev
- https://github.com/highlightjs/highlight.js
- https://github.com/highlightjs/highlight.js/blob/main/LICENSE
- https://github.com/highlightjs/highlight.js/blob/main/README.md
- https://github.com/highlightjs/highlight.js/tree/main/src/styles
- https://github.com/react-syntax-highlighter/react-syntax-highlighter/blob/master/README.md
- https://github.com/react-syntax-highlighter/react-syntax-highlighter/blob/master/LICENSE
- https://github.com/react-syntax-highlighter/react-syntax-highlighter/releases
- https://github.com/FormidableLabs/prism-react-renderer/blob/master/README.md
- https://github.com/FormidableLabs/prism-react-renderer/blob/master/LICENSE
- https://github.com/FormidableLabs/prism-react-renderer/releases
- https://github.com/shikijs/shiki
- https://github.com/shikijs/shiki/releases

Documentation sites
- https://codemirror.net/
- https://codemirror.net/docs/guide/
- https://codemirror.net/docs/ref/
- https://codemirror.net/examples/decoration/
- https://code.haverbeke.berlin/codemirror/theme-one-dark
- https://shiki.style/guide/
- https://shiki.style/guide/install
- https://shiki.style/guide/bundles
- https://shiki.style/guide/decorations
- https://shiki.style/guide/regex-engines
- https://shiki.style/guide/transformers
- https://shiki.style/themes
- https://shiki.style/packages/transformers
- https://shiki.style/packages/markdown-it
- https://highlightjs.org/usage/

GitHub API queries
- https://api.github.com/repos/microsoft/monaco-editor
- https://api.github.com/repos/suren-atoyan/monaco-react
- https://api.github.com/repos/codemirror/dev
- https://api.github.com/repos/uiwjs/react-codemirror
- https://api.github.com/repos/shikijs/shiki
- https://api.github.com/repos/highlightjs/highlight.js
- https://api.github.com/repos/react-syntax-highlighter/react-syntax-highlighter
- https://api.github.com/repos/FormidableLabs/prism-react-renderer
- https://api.github.com/repos/microsoft/monaco-editor/issues?state=all&per_page=100&sort=updated, and the same query for each repository listed above

Local measurements
- Bundle sizes: esbuild 0.28.2, minified ESM bundles built and gzipped on 2026-11-23 in a scratch directory outside the repository, one entry per candidate, React external for wrappers. The measured byte counts are quoted in each section.

## Wiring it into this repository

Status: an estimate, not a description of implemented code. It was verified against the source on 2026-11-23 by reading the files named below.

What already exists, and why it matters.

- The UI already depends on `shiki ^4.6.0` (`src/verifiable_tutor/ui/web/package.json`) and has a fine-grained, lazily loaded, offline highlighter in `src/verifiable_tutor/ui/web/src/lib/highlighter.tsx`: `createHighlighterCore`, the JavaScript RegExp engine, one dynamic import per language, and a token-to-React-node renderer. Its language map has no `c`, `cpp` or `h` entry.
- `src/verifiable_tutor/ui/web/src/components/ui/code-block.tsx` already renders a copy button, CSS-counter line numbers (`lineNumbers`, `startLine`) and a `highlighted` line variant, so the frame of a VS Code style pane exists without new dependencies.
- The built app already ships a lazily loaded C grammar chunk (`assets/c-CRSonjJO.js`) and a markdown chunk, because `@streamdown/code` pulls the full Shiki language set. The marginal cost of a C view is therefore a code path, not a download.
- The lazy viewer pattern is established: `src/verifiable_tutor/ui/web/src/components/knowledge/pdf-viewer.tsx` dynamically imports `pdfjs-dist` and its worker with `?url`, and the document page fetches the file as an `ArrayBuffer` from `/api/knowledge/documents/{doc_id}/file`.
- The backend already has the shape needed to serve a second file kind: `src/verifiable_tutor/knowledge/browse.py` resolves `pdf_path` and `src/verifiable_tutor/api/routers/corpus.py` shows the path-allowlist check (`root not in path.parents`).
- The gap: `kb_documents` has `pdf_path TEXT NOT NULL` and no kind column (`src/verifiable_tutor/storage.py`, `SCHEMA_VERSION = 7`), so a text file cannot be stored as a document without a schema change.

### Option A: viewer only

The file is displayed from an allowlisted directory. It is not a knowledge document, so the agent cannot retrieve it, quote it or cite it.

| Area | Change | File | Rough size |
|---|---|---|---|
| Viewer | New component: fetch text, highlight with the existing highlighter, render `CodeBlock` with line numbers, scroll to and mark a line range | `components/knowledge/text-viewer.tsx` | 180 lines |
| Grammar | Add `c`, `cpp`, `h` to the language map | `lib/highlighter.tsx` | 4 lines |
| Page | Branch the viewer on the file kind and keep the existing side panes | `routes/knowledge/document-page.tsx` | 40 lines |
| Client | Fetch the text body, carry `source_kind` | `lib/api/knowledge.ts` | 25 lines |
| Copy | Viewer strings in both locales, which the parity test guards | `lib/i18n/en.ts`, `lib/i18n/zh.ts` | 6 keys |
| Backend | `GET /api/knowledge/documents/{doc_id}/text`: 401, 404, 422, size cap, extension allowlist, path traversal check | new `api/routers/files.py` | 90 lines |
| Config | One configured directory, following `corpus_pdf_dir` | `settings.py`, `config/app.yaml` | 6 lines |
| Tests | Viewer renders N lines, marks a range, escapes HTML; API rejects traversal and unauthenticated reads | `tests/api/test_files.py`, `web/tests/text-viewer.test.tsx` | 200 lines |
| Docs | Page map row and API bundle | `docs/ui-structure.md`, `docs/api/` | regenerated |

Total: about 10 files, about 650 lines including tests, 4 or 5 commits, no new dependency. In agent terms this is four changes of one or two files each: the endpoint and its tests, the viewer and its tests, the page branch and copy, and the documentation and bundle refresh.

### Option B: a citable knowledge document

Option A plus the corpus path, so the agent can search, quote and cite `file.c:120-134` the way it cites a page today.

| Area | Change | File | Rough size |
|---|---|---|---|
| Schema | `source_kind` and `text_path` columns, `SCHEMA_VERSION` 8, one migration tuple, plus the schema test | `storage.py`, `tests/storage/test_storage_schema.py` | 20 lines |
| Store | Carry the two fields through `upsert_document` and the row mapping | `corpus/store.py` | 20 lines |
| Pages | Split a text file into pseudo pages of N lines, each with one block per line range, and emit `vt-page-record/1` shaped records so the existing chunker and index job consume them unchanged | new `corpus/text_pages.py` plus tests | 150 lines |
| Ingest | A text source list that skips the OCR job and writes the page records | `scripts/ingest_corpus.py` | 60 lines |
| API | `text_path` in the browse service and the `/text` route, new response fields, regenerated bundle | `knowledge/browse.py`, `api/schemas.py`, `api/routers/knowledge_browse.py` | 70 lines |
| Citation panel | A text thumbnail and pane that opens at the cited line range instead of a page image | `components/chat/source-thumbnail.tsx`, `source-pane.tsx` | 70 lines |
| Browser | A kind badge on the tile and a line count in the file pane | `components/knowledge/tiles.tsx`, `file-info-pane.tsx` | 40 lines |
| Record docs | The new page record fields and the ingest contract | `docs/corpus-schema.md`, `docs/ui-structure.md` | by hand |
| TACC | One index job and one summary job over the new document. No new job template, because everything after the OCR stage is already page based | none | 2 jobs |

Total: about 20 files, about 1,800 lines including tests, 8 to 10 commits, two TACC jobs, no new dependency.

### The one requirement Shiki does not meet

In-document find. If the viewer must have a first-party find panel with match navigation, the fallback in this note is CodeMirror 6 at about 208 KB gz, read-only facets, `Decoration.line` for the range and a hand-written VS Code theme. In this app that replaces one file, `text-viewer.tsx`, and adds one theme file, so the decision can be deferred until the reviewer asks for search; the rest of Option A and B does not depend on it. Monaco is not recommended: the worker plus 722 KB gz chunk for a 240 line read-only file, and its token colors come from Monarch rules rather than VS Code's TextMate themes.

### Risks worth stating before the work starts

- Two citation models. A PDF citation is `page_no` plus a box, a text citation is `line_start..line_end`. Keeping both in one `chunks`/evidence path means the renderer must label which one it holds; Shiki's decorations are 0-indexed while stored lines should be 1-indexed.
- Markdown has two possible products, the coloured source and the rendered page. The source view keeps one citation model for both file kinds; the rendered view needs relative link and image rewriting and would not map to lines. `@streamdown` based `Markdown` already exists for the rendered case if it is wanted as a toggle.
- Serving files from disk needs the same guard as `corpus.py`: an allowlisted root, a resolved path check, an extension allowlist and a size cap.

