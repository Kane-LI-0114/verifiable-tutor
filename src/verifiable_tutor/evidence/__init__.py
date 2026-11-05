"""Retrieval: query planning, lexical and dense arms, and rank fusion.

This stage produces chunks only. Turning a hit into a stored citation and
injecting chunks into the chat prompt are recorded as TODO in ADR-0015 and in
the PRD; `GET /api/knowledge/retrieve` is the entry point the tool will call.
"""
