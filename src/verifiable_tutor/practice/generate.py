"""Practice question generation (VT-17 minimal slice).

Generate self-test questions for a topic through the existing agent loop, with
the practice generation prompt as the system prompt. The agent retrieves course
chunks and returns questions with reference answers and numbered sources.
"""

from __future__ import annotations

from typing import Any

from ..prompts import load_prompt

PRACTICE_PROMPT = load_prompt("practice_generation")


def generate_practice(
    topic: str,
    runner: Any,
    adapter: Any,
    *,
    provider: str = "deepseek",
    tier: str = "flash",
) -> tuple[str, list[dict]]:
    """Generate self-test questions for a topic through the agent loop.

    Returns the final answer text and the numbered sources. The runner and
    adapter are seams: production passes the project agent runner and adapter,
    tests pass fakes.
    """

    messages = [
        {"role": "system", "content": PRACTICE_PROMPT},
        {
            "role": "user",
            "content": f"Generate self-test questions on the topic: {topic}",
        },
    ]
    text = ""
    sources: list[dict] = []
    for event in runner.run(
        messages, adapter=adapter, provider=provider, tier=tier
    ):
        if event.kind == "turn_end":
            text = event.data.get("text", "")
            sources = list(event.data.get("sources", []))
    return text, sources
