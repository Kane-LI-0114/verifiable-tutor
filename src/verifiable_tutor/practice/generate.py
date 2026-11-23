"""Practice question generation (VT-17).

Generate structured self-test questions through the agent loop. The model
returns one JSON array of question objects, which is parsed into
``GeneratedQuestion`` records for the UI and the grading endpoint.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..prompts import load_prompt

PRACTICE_PROMPT = load_prompt("practice_generation")


@dataclass(frozen=True)
class GeneratedQuestion:
    """One structured generated question."""

    type: str
    topic: str
    question: str
    choices: list[str]
    answer: str
    reference_answer: str
    scoring_points: list[str]
    max_score: float
    knowledge_points: list[str]


def load_knowledge_points(repo_root: Path) -> dict[str, list[str]]:
    """Load the per-topic knowledge points from config/knowledge_points.yaml."""

    path = repo_root / "config" / "knowledge_points.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        str(topic): [str(point) for point in points]
        for topic, points in data.get("topics", {}).items()
    }


def _parse_questions(text: str, *, default_topic: str = "") -> list[GeneratedQuestion]:
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
                # A single-topic request keeps the topic the student chose;
                # the model sometimes tags a knowledge point in "topic".
                topic=default_topic or str(item.get("topic") or ""),
                question=str(item.get("question", "")),
                choices=[str(choice) for choice in (item.get("choices") or [])],
                answer=str(item.get("answer", "")),
                reference_answer=str(item.get("reference_answer", "")),
                scoring_points=[
                    str(point) for point in (item.get("scoring_points") or [])
                ],
                max_score=float(item.get("max_score", 0)),
                knowledge_points=[
                    str(point) for point in (item.get("knowledge_points") or [])
                ],
            )
        )
    return questions


def generate_practice(
    topic: str,
    runner: Any,
    adapter: Any,
    *,
    types: list[str] | None = None,
    knowledge_points: dict[str, list[str]] | None = None,
    provider: str = "deepseek",
    tier: str = "flash",
) -> tuple[list[GeneratedQuestion], list[dict]]:
    """Generate structured self-test questions for a topic.

    ``knowledge_points`` maps each topic to its points. For a single topic the
    questions get that topic; for "all topics" the model tags each question
    with the topic it belongs to.
    """

    if topic == "all topics":
        user_content = "Generate self-test questions covering all course topics"
        default_topic = ""
        if knowledge_points:
            user_content += (
                "\n\nThe course topics and their knowledge points are:\n"
            )
            for topic_name, points in knowledge_points.items():
                user_content += f"- {topic_name}: " + ", ".join(points) + "\n"
            user_content += (
                '\nFor each question, set "topic" to the topic it belongs to and '
                '"knowledge_points" to the points it covers.'
            )
    else:
        user_content = f"Generate self-test questions on the topic: {topic}"
        default_topic = topic
        if knowledge_points:
            points = knowledge_points.get(topic, [])
            user_content += (
                "\n\nThe topic's knowledge points are:\n"
                + "\n".join(f"- {point}" for point in points)
                + '\nFor each question, set "knowledge_points" to the points it covers.'
            )
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
    return _parse_questions(text, default_topic=default_topic), sources
