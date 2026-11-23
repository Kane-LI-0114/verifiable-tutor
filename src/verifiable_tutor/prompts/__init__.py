"""Model prompt texts in one editable home.

Every prompt the application sends to a model lives as one ``.md`` file in
this directory, and package code loads it with :func:`load_prompt` instead of
inlining prompt text in Python. Editing a file and reloading (the dev server
auto reloads from ``src/``) changes the prompt without a code change.

Current texts: ``chat_system.md`` is the chat system prompt, and ``kb_v1.md``
is the knowledge-base job template (``prompt_version`` kb-v1) whose system,
user, and repair sections the TACC worker parses; the local driver stages a
copy of it into the task directory. ``practice_generation.md`` is the self-test
generation system prompt, and ``deadline_status.md`` is the per-turn assignment
deadline note. Model request parameters stay in
``config/models.yaml``; see AGENTS.md.
"""

from __future__ import annotations

from pathlib import Path

#: The directory that holds every prompt text shipped with the package.
PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Return the text of the prompt file ``<name>.md`` from this directory."""

    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"prompt {name!r} not found: {path}")
    return path.read_text(encoding="utf-8").strip()
