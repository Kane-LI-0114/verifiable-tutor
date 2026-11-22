"""Practice question generation (VT-17).

Generate structured self-test questions through the agent loop. The model
returns one JSON array of question objects, which is parsed into
``GeneratedQuestion`` records for the UI and the grading endpoint.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ..prompts import load_prompt

PRACTICE_PROMPT = load_prompt("practice_generation")


@dataclass(frozen=True)
class GeneratedQuestion:
    """One structured generated question."""

    type: str
    question: str
    choices: list[str]
    reference_answer: str
    scoring_points: list[str]
    max_score: float


def _parse_questions(text: str) -> list[GeneratedQuestion]:
    """Extract the JSON question array from the model output.

    The agent loop may leave its reasoning text before the final JSON array,
    so the parser finds the first ``[`` and the last ``]`` and loads that
    slice. A missing or malformed array yields an empty list.
    """

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    questions: list[GeneratedQuestion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        questions.append(
            GeneratedQuestion(
                type=str(item.get("type", "")),
                question=str(item.get("question", "")),
                choices=[str(choice) for choice in (item.get("choices") or [])],
                reference_answer=str(item.get("reference_answer", "")),
                scoring_points=[
                    str(point) for point in (item.get("scoring_points") or [])
                ],
                max_score=float(item.get("max_score", 0)),
            )
        )
    return questions


def generate_practice(
    topic: str,
    runner: Any,
    adapter: Any,
    *,
    types: list[str] | None = None,
    provider: str = "deepseek",
    tier: str = "flash",
) -> tuple[list[GeneratedQuestion], list[dict]]:
    """Generate structured self-test questions for a topic.

    Returns the parsed question list and the numbered sources. The runner and
    adapter are seams: production passes the project agent runner and adapter,
    tests pass fakes.
    """

    if topic == "all topics":
        user_content = "Generate self-test questions covering all course topics"
    else:
        user_content = f"Generate self-test questions on the topic: {topic}"
    if types:
        user_content += (
            ". Only generate these question types: " + ", ".join(types) + "."
        )
    messages = [
        {"role": "system", "content": PRACTICE_PROMPT},
        {"role": "user", "content": user_content},
    ]
    text = ""
    sources: list[dict] = []
    for event in runner.run(
        messages, adapter=adapter, provider=provider, tier=tier
    ):
        if event.kind == "turn_end":
            text = event.data.get("text", "")
            sources = list(event.data.get("sources", []))
    return _parse_questions(text), sources
