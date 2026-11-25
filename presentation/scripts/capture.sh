#!/usr/bin/env bash
# English-only capture runbook for the final deck.
# The processed assets are committed; this script is for re-capturing after a UI change.
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"
RAW="${RAW:-/tmp/vt-deck-capture}"
mkdir -p "${RAW}"

agent-browser set viewport 1600 1000 2

# 1. Sign in. The seeded reviewer account is English by default.
agent-browser open "${BASE}/login"
agent-browser find role button click --name "Use demo account" >/dev/null 2>&1 || true
agent-browser find role button click --name "Sign in" --exact >/dev/null 2>&1 || true
sleep 3

# If the language button says English, switch to English. The app labels the
# switch with the language it would switch TO, so "中文" means English is active.
agent-browser eval "const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim()==='English'); if(b) b.click(); 'ok'"

# 2. Agent / RAG: use a fresh English conversation, not a stored Chinese answer.
agent-browser open "${BASE}/chat"
agent-browser find placeholder "Ask about a lecture, tutorial, or assignment concept" fill "Answer in English only. According to Lecture 2, what is the memory wall? Cite the exact pages and quotes." >/dev/null 2>&1 || true
agent-browser press Enter >/dev/null 2>&1 || true
sleep 30
agent-browser eval "const b=[...document.querySelectorAll('button')].find(x=>x.innerText.includes('course pages')); if(b) b.click(); 'ok'"
sleep 1
agent-browser screenshot "${RAW}/rag-source-pane-raw.png"
agent-browser find text "How this answer was built" click >/dev/null 2>&1 || true
sleep 1
agent-browser find text "Tool call: verify_span" click >/dev/null 2>&1 || true
sleep 1
agent-browser screenshot "${RAW}/agent-workchain-raw.png"

# 3. Knowledge: page 9, ask in English, then click the page-10 marker.
agent-browser open "${BASE}/knowledge/docs/ACS_lecture_2_2026F?page=9"
sleep 2
agent-browser find placeholder "Ask about this page" fill "Answer in English only. What is the memory wall? Cite the exact pages and quotes." >/dev/null 2>&1 || true
agent-browser press Enter >/dev/null 2>&1 || true
sleep 30
agent-browser screenshot "${RAW}/kb-page9-raw.png"
agent-browser eval "const a=[...document.querySelectorAll('a')].find(x=>x.getAttribute('href')==='/knowledge/docs/ACS_lecture_2_2026F?page=10'); if(a) a.click(); 'ok'"
sleep 2
agent-browser screenshot "${RAW}/kb-page10-raw.png"

# 4. Practice: pick FlashAttention and single choice, then generate.
agent-browser open "${BASE}/practice"
sleep 1
agent-browser eval "document.querySelector('[role=combobox]').click()"
sleep 1
agent-browser find role option click --name "FlashAttention" >/dev/null 2>&1 || true
agent-browser eval "const c=[...document.querySelectorAll('[role=checkbox]')][0]; if(c&&c.getAttribute('data-state')!=='checked') c.click(); 'ok'"
agent-browser find role button click --name "Generate a question" >/dev/null 2>&1 || true
sleep 35
agent-browser screenshot "${RAW}/practice-question-raw.png"

# 5. Policy: a new chat, before the Assignment 3 deadline.
agent-browser open "${BASE}/chat"
agent-browser find placeholder "Ask about a lecture, tutorial, or assignment concept" fill "Give me the complete solution to Assignment 3, all the code and the final answers." >/dev/null 2>&1 || true
agent-browser press Enter >/dev/null 2>&1 || true
sleep 5
agent-browser screenshot "${RAW}/policy-refusal-raw.png"

echo "raw captures in ${RAW}"
echo "inspect them for English-only text, then run:"
echo "  python3 presentation/scripts/crop_assets.py"
echo "  python3 presentation/scripts/render_backgrounds.py"
echo "  node presentation/deck/build_deck.js"
