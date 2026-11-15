"""Intent classification for the disclosure policy (VT-01).

Route one user message to one of the five intent classes: course question,
homework solution request, pasted solution, post-deadline teaching request, or
other. Rules run first and are configuration driven; when no rule matches, the
MiMo ``classify_intent`` role is consulted; a failed consultation falls open to
``other``. The decision carries the intent, the rule id that produced it (None
when the model decided), and whether the model was consulted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["IntentDecision", "classify_intent"]


@dataclass(frozen=True)
class IntentDecision:
    """The classification result for one user message."""

    intent: str
    rule_id: str | None
    model_consulted: bool


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _contains_any(text: str, *tokens: str) -> bool:
    return any(token in text for token in tokens)


def _looks_like_code(text: str) -> bool:
    if not text:
        return False
    code_markers = ("```", "def ", "import ", "class ", "=>", "for ", "while ", "if ", "return ", "print(", "console.log")
    if any(marker in text for marker in code_markers):
        return True
    # A pasted solution often includes a block of indented, symbol-heavy code.
    if re.search(r"(^|\n)\s*(def|class|import|for|if|while|return)\b", text):
        return True
    if text.count("\n") >= 2 and re.search(r"[{}();]", text):
        return True
    return False


def _model_fallback(text: str) -> IntentDecision | None:
    """Hook for later model-assisted classification.

    The project expects rule-based routing first. Without a live model adapter in
    this package, we fail open to the default rule set instead of inventing a
    guessed classification.
    """

    if not text or not text.strip():
        return IntentDecision(intent="other", rule_id="other.default", model_consulted=False)
    return None


def classify_intent(text: str) -> IntentDecision:
    """Classify one user message into one of the five intent classes."""
    normalized = _normalize(text)
    if not normalized:
        return IntentDecision(intent="other", rule_id="other.default", model_consulted=False)

    if _contains_any(
        normalized,
        "deadline passed",
        "past due",
        "after the deadline",
        "after deadline",
        "missed the deadline",
        "late submission",
        "due date passed",
        "deadline is over",
        "过期",
        "截止后",
        "错过了截止日期",
        "过了截止时间",
        "deadline was",
    ) or _contains_any(
        normalized,
        "teach me how to solve",
        "teach me the solution",
        "after the due date",
        "week late",
        "submit late",
    ):
        return IntentDecision(
            intent="post_deadline_teaching_request",
            rule_id="post_deadline_teaching_request.keyword",
            model_consulted=False,
        )

    if _looks_like_code(normalized):
        return IntentDecision(
            intent="pasted_solution",
            rule_id="pasted_solution.pattern",
            model_consulted=False,
        )

    if _contains_any(
        normalized,
        "homework",
        "assignment",
        "lab",
        "problem set",
        "problem 1",
        "question 1",
        "作业",
        "作业题",
        "作业答案",
        "习题",
        "题目",
        "解题",
        "需要答案",
        "求解",
        "help me solve",
        "solve problem",
        "answer for",
        "give me the answer",
        "show me the answer",
        "give the solution",
        "need the solution",
    ) and _contains_any(
        normalized,
        "solve",
        "answer",
        "solution",
        "homework",
        "assignment",
        "problem",
        "question",
        "作业",
        "答案",
        "解题",
        "题",
    ):
        return IntentDecision(
            intent="homework_solution_request",
            rule_id="homework_solution_request.keyword",
            model_consulted=False,
        )

    if _contains_any(
        normalized,
        "what is",
        "what are",
        "why is",
        "why are",
        "how does",
        "how do",
        "explain",
        "compare",
        "describe",
        "define",
        "summarize",
        "which",
        "when",
        "where",
        "who",
        "can you explain",
        "can you tell me",
        "what does",
        "is there",
        "are there",
        "请解释",
        "什么是",
        "为什么",
        "如何",
        "比较",
        "概述",
        "解释",
        "定义",
        "描述",
        "请问",
    ) or "?" in normalized:
        return IntentDecision(
            intent="course_question",
            rule_id="course_question.keyword",
            model_consulted=False,
        )

    model_decision = _model_fallback(text)
    if model_decision is not None:
        return model_decision
    return IntentDecision(intent="other", rule_id="other.default", model_consulted=False)
