"""Prompt texts are provided by the prompts package, not by inline code."""

from verifiable_tutor.prompts import load_prompt


def test_chat_system_prompt_comes_from_the_prompts_package():
    text = load_prompt("chat_system")

    assert "You are a tutor for the CSIT6000V course at HKUST." in text
    assert "do not invent citations or course facts" in text


def test_practice_generation_prompt_comes_from_the_prompts_package():
    text = load_prompt("practice_generation")

    assert "self-test generator for the CSIT6000V course" in text
    assert "verify_span" in text
    assert "single choice, multiple choice, true or false, short answer" in text
    assert "code." in text

