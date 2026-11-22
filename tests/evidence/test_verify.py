from verifiable_tutor.evidence.verify import normalize, verify_span


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
