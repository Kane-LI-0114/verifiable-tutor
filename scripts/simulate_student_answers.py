"""Simulate RQ2b student answers with MiMo Pro.

Implements benchmark-protocol.md section 4 step 2: for every question in the
frozen shared set, role-play four student answer variants (correct,
partially_correct, wrong, ambiguous) and write them to ``answers.jsonl``.

The simulator never sees scoring points or ground truth, and the prompt forbids
external search. Model and endpoint mirror config/models.yaml (``mimo.pro``);
the API key is read from ``MIMO_API_KEY`` in ``.env``.

Usage:
    python scripts/simulate_student_answers.py grading_shared/<run-id>
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://api.xiaomimimo.com/v1"
MODEL = "mimo-v2.6-pro"
TEMPERATURE = 0.3
VARIANTS = ("correct", "partially_correct", "wrong", "ambiguous")

PROMPT = """You are role-playing a student answering a self-test question. Do not use external search.

Question:
{QUESTION}

{OPTIONS}

Produce FOUR different student answers to this question:
1. "correct": a fully correct answer.
2. "partially_correct": right direction but incomplete.
3. "wrong": a fully wrong answer.
4. "ambiguous": a vague or edge-case answer.

Return a single JSON object with exactly these four keys: "correct", "partially_correct", "wrong", "ambiguous". Each value is a string. Return only JSON."""


def _build_prompt(question: dict) -> str:
    options = question.get("options")
    options_block = (
        "Options:\n" + "\n".join(options) if options else "Options: (none)"
    )
    return (
        PROMPT.replace("{QUESTION}", question["question_text"])
        .replace("{OPTIONS}", options_block)
    )


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text[3:]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
        text = text.strip()
    return json.loads(text)


def _simulate(client: OpenAI, question: dict) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": _build_prompt(question)}],
        temperature=TEMPERATURE,
    )
    return _parse_json(response.choices[0].message.content or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate RQ2b student answers.")
    parser.add_argument("run_dir", help="grading_shared/<run-id> directory")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    api_key = os.environ.get("MIMO_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("MIMO_API_KEY is empty; set it in .env")

    run = Path(args.run_dir)
    questions = [
        json.loads(line)
        for line in (run / "questions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    client = OpenAI(base_url=BASE_URL, api_key=api_key)
    today = date.today().isoformat()
    rows = []
    for question in questions:
        variants = _simulate(client, question)
        for variant in VARIANTS:
            rows.append(
                {
                    "question_id": question["question_id"],
                    "variant": variant,
                    "answer_text": variants[variant],
                    "simulator": MODEL,
                    "simulator_date": today,
                }
            )

    out = run / "answers.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} answers to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
