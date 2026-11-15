from verifiable_tutor.policy.intent import IntentDecision, classify_intent

def test_classify_course_question() -> None:
    decision = classify_intent("What is the difference between a process and a thread?")

    assert isinstance(decision, IntentDecision)
    assert decision.intent == "course_question"
    assert decision.rule_id == "course_question.keyword"
    assert decision.model_consulted is False


def test_classify_homework_solution_request() -> None:
    decision = classify_intent("Please solve problem 3 in the homework and show the steps.")

    assert decision.intent == "homework_solution_request"
    assert decision.rule_id == "homework_solution_request.keyword"


def test_classify_pasted_solution() -> None:
    decision = classify_intent("Here is my solution:\n```python\nprint('hello')\n```")

    assert decision.intent == "pasted_solution"
    assert decision.rule_id == "pasted_solution.pattern"


def test_classify_post_deadline_teaching_request() -> None:
    decision = classify_intent("The deadline passed, can you teach me how to solve question 2?")

    assert decision.intent == "post_deadline_teaching_request"
    assert decision.rule_id == "post_deadline_teaching_request.keyword"


def test_classify_other() -> None:
    decision = classify_intent("I am feeling good today.")

    assert decision.intent == "other"
    assert decision.rule_id == "other.default"
 