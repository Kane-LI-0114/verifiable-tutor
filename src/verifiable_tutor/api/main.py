"""Module-level application for the FastAPI CLI and uvicorn.

Tests use ``verifiable_tutor.api.factory.create_app`` with explicit settings so
they never depend on the local ``.env``.
"""

from .factory import create_app

app = create_app()
