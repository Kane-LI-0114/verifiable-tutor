"""Knowledge-base build helpers for the Qwen spike.

This package holds the parts of the knowledge-base pipeline that can be tested
and reused locally: turning OCR page records into the input chunk contract,
building the ``vt-kb-request/1`` manifest, and validating the records the TACC
job returns. The TACC job itself only writes results; the local driver decides
whether a build passed.

The chunk helper is spike-scoped: one chunk per non-empty page. The product
chunker will live in ``src/verifiable_tutor/corpus/`` and split at section
boundaries.
"""

from verifiable_tutor.knowledge.chunks import chunks_from_pages, normalize_doc_id
from verifiable_tutor.knowledge.request import build_request, corpus_hash
from verifiable_tutor.knowledge.schema import (
    normalize_text,
    quote_on_page,
    validate_progress,
    validate_record,
)

__all__ = [
    "build_request",
    "chunks_from_pages",
    "corpus_hash",
    "normalize_doc_id",
    "normalize_text",
    "quote_on_page",
    "validate_progress",
    "validate_record",
]
