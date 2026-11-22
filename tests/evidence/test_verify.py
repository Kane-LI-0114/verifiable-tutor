from types import SimpleNamespace

from verifiable_tutor.evidence.verify import (
    normalize,
    verify_citation,
    verify_span,
    verify_span_llm,
)


def test_normalize_collapses_whitespace() -> None:
    assert normalize("  hello \t world\n ") == "hello world"


def test_normalize_lowercases() -> None:
    assert normalize("Hello World") == "hello world"


def test_verify_span_exact_match() -> None:
    assert verify_span("MPI is a standard", "MPI is a standard for parallelism") is True


def test_verify_span_ignores_whitespace_difference() -> None:
    assert verify_span("MPI   is", "MPI is a standard") is True


def test_verify_span_ignores_case_difference() -> None:
    assert verify_span("mpi is", "MPI is a standard") is True


def test_verify_span_ignores_both_differences() -> None:
    assert verify_span("  Mpi   Is  ", "MPI is a standard") is True


def test_verify_span_not_present() -> None:
    assert verify_span("CUDA", "MPI is a standard") is False


def test_verify_span_empty_span() -> None:
    assert verify_span("", "MPI is a standard") is False


def test_verify_span_empty_text() -> None:
    assert verify_span("MPI", "") is False


def test_verify_citation_passes_when_span_is_on_the_page() -> None:
    verdict = verify_citation(
        "MPI reduces", "MPI reduces a value", "MPI reduces a value across ranks"
    )

    assert verdict.verified is True
    assert verdict.in_chunk is True
    assert verdict.in_page is True
    assert verdict.normalized_span == "mpi reduces"


def test_verify_citation_fails_when_span_is_absent() -> None:
    verdict = verify_citation("CUDA", "MPI reduces", "MPI reduces across ranks")

    assert verdict.verified is False
    assert verdict.in_chunk is False
    assert verdict.in_page is False


def test_verify_citation_span_on_page_but_not_in_the_shown_chunk() -> None:
    verdict = verify_citation("across ranks", "MPI reduces", "MPI reduces across ranks")

    assert verdict.verified is True
    assert verdict.in_chunk is False
    assert verdict.in_page is True


def test_verify_citation_empty_span_never_passes() -> None:
    verdict = verify_citation("", "MPI reduces", "MPI reduces")

    assert verdict.verified is False


class FakeReviewer:
    def __init__(self, verdict: str = "match") -> None:
        self._verdict = verdict
        self.calls: list[list[dict]] = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return SimpleNamespace(text=self._verdict)


def test_verify_span_llm_returns_true_on_match() -> None:
    reviewer = FakeReviewer("match")

    assert verify_span_llm("MPI reduces", "MPI reduces a value", reviewer) is True


def test_verify_span_llm_returns_false_on_no_match() -> None:
    reviewer = FakeReviewer("no_match")

    assert verify_span_llm("CUDA", "MPI reduces", reviewer) is False


def test_verify_span_llm_empty_span_skips_the_reviewer() -> None:
    reviewer = FakeReviewer("match")

    assert verify_span_llm("", "MPI reduces", reviewer) is False
    assert reviewer.calls == []
