#!/usr/bin/env python3
"""Live smoke for the agent loop with DeepSeek and MiMo (ADR-0016).

This script makes real paid model, search, and fetch calls. It is not part of
pytest. It probes the three tool backends directly, then runs one course turn
and one web turn for each requested provider and writes a JSON summary under the
ignored data directory.

Usage:
    .venv/bin/python scripts/smoke_agent_loop.py --provider deepseek --tier flash
    .venv/bin/python scripts/smoke_agent_loop.py --provider mimo --tier flash
    .venv/bin/python scripts/smoke_agent_loop.py --provider all

Exit codes: 0 all checks passed, 1 at least one check failed, 2 setup failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from verifiable_tutor.api.factory import _build_embedder  # noqa: E402
from verifiable_tutor.corpus.store import KnowledgeStore  # noqa: E402
from verifiable_tutor.evidence.retrieval import HybridRetriever  # noqa: E402
from verifiable_tutor.llm.adapter import ModelAdapter  # noqa: E402
from verifiable_tutor.llm.config import load_model_config  # noqa: E402
from verifiable_tutor.orchestrator.builtin_tools import build_tool_registry  # noqa: E402
from verifiable_tutor.orchestrator.runner import AgentRunner  # noqa: E402
from verifiable_tutor.orchestrator.tools import ToolContext  # noqa: E402
from verifiable_tutor.prompts import load_prompt  # noqa: E402
from verifiable_tutor.settings import load_settings  # noqa: E402
from verifiable_tutor.storage import Storage  # noqa: E402

COURSE_QUESTION = (
    "Explain MPI_Allreduce and when to use it, citing the course slides."
)
WEB_QUESTION = (
    "What is the latest DeepSeek model release? Search the web and cite the URL."
)
FETCH_URLS = (
    "https://api-docs.deepseek.com/guides/search",
    "https://example.com",
)


def _summary(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    return text[:limit]


def _probe_tools(registry, context) -> dict:
    checks: dict[str, dict] = {}

    started = time.perf_counter()
    result = registry.execute(
        "search_course", {"query": "MPI_Allreduce", "k": 3}, context=context
    )
    payload = json.loads(result.content) if result.status == "done" else {}
    checks["search_course"] = {
        "ok": result.status == "done" and bool(payload.get("chunks")),
        "status": result.status,
        "chunks": len(payload.get("chunks") or []),
        "elapsed_s": round(time.perf_counter() - started, 3),
    }

    started = time.perf_counter()
    result = registry.execute(
        "web_search", {"query": "DeepSeek V4 release", "count": 3}, context=context
    )
    payload = json.loads(result.content) if result.status == "done" else {}
    checks["web_search"] = {
        "ok": result.status == "done" and bool(payload.get("results")),
        "status": result.status,
        "results": len(payload.get("results") or []),
        "elapsed_s": round(time.perf_counter() - started, 3),
    }

    fetch_check = {"ok": False, "status": "failed", "chars": 0, "url": None}
    for url in FETCH_URLS:
        started = time.perf_counter()
        result = registry.execute("web_fetch", {"url": url}, context=context)
        payload = json.loads(result.content) if result.status == "done" else {}
        chars = len(payload.get("content") or "")
        fetch_check = {
            "ok": result.status == "done" and chars > 0,
            "status": result.status,
            "chars": chars,
            "url": url,
            "elapsed_s": round(time.perf_counter() - started, 3),
        }
        if fetch_check["ok"]:
            break
    checks["web_fetch"] = fetch_check
    return checks


def _run_turn(runner, adapter, provider: str, tier: str, question: str) -> dict:
    messages = [
        {"role": "system", "content": load_prompt("chat_system")},
        {"role": "user", "content": question},
    ]
    started = time.perf_counter()
    tool_names: list[str] = []
    final_text = ""
    model_calls = 0
    usage: dict = {}
    for event in runner.run(
        messages,
        adapter=adapter,
        provider=provider,
        tier=tier,
        thinking="off",
    ):
        if event.kind == "tool_end":
            tool_names.append(str(event.data.get("name")))
        elif event.kind == "turn_end":
            final_text = str(event.data.get("text") or "")
            model_calls = int(event.data.get("model_calls") or 0)
            usage = dict(event.data.get("usage") or {})
    return {
        "ok": bool(tool_names) and bool(final_text.strip()),
        "question": question,
        "tool_names": tool_names,
        "model_calls": model_calls,
        "final_chars": len(final_text),
        "final_preview": _summary(final_text),
        "usage": usage,
        "elapsed_s": round(time.perf_counter() - started, 3),
    }


def _provider_check(adapter, runner, provider: str, tier: str) -> dict:
    course = _run_turn(runner, adapter, provider, tier, COURSE_QUESTION)
    web = _run_turn(runner, adapter, provider, tier, WEB_QUESTION)
    course["ok"] = course["ok"] and "search_course" in course["tool_names"]
    web["ok"] = web["ok"] and "web_search" in web["tool_names"]
    return {"provider": provider, "tier": tier, "course": course, "web": web}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=("deepseek", "mimo", "all"),
        default="all",
        help="Provider to test; all runs DeepSeek then MiMo.",
    )
    parser.add_argument("--tier", default="flash", help="Model tier alias.")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the adapter response cache and force paid calls.",
    )
    args = parser.parse_args(argv)

    try:
        settings = load_settings(repo_root=REPO_ROOT)
        resolved = load_model_config(
            REPO_ROOT / "config" / "models.yaml",
            env_file=REPO_ROOT / ".env",
            base_dir=REPO_ROOT,
        )
        if args.no_cache:
            resolved.config.cache.enabled = False
        adapter = ModelAdapter(resolved)
        storage = Storage(settings.database_path)
        storage.initialize()
        store = KnowledgeStore(storage)
        retriever = HybridRetriever(store=store, embedder=_build_embedder(settings))
        registry = build_tool_registry(settings=settings)
        runner = AgentRunner(
            settings=settings,
            registry=registry,
            retriever=retriever,
            store=store,
        )
    except Exception as exc:  # setup failure, not a model result
        print(f"setup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    context = ToolContext(
        adapter=adapter,
        retriever=retriever,
        store=store,
        settings=settings,
    )
    providers = (
        ["deepseek", "mimo"] if args.provider == "all" else [args.provider]
    )
    summary = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "tier": args.tier,
        "cache": not args.no_cache,
    }
    failures = 0
    for provider in providers:
        try:
            tool_checks = _probe_tools(registry, context)
            turn_checks = _provider_check(adapter, runner, provider, args.tier)
            provider_ok = (
                all(check["ok"] for check in tool_checks.values())
                and turn_checks["course"]["ok"]
                and turn_checks["web"]["ok"]
            )
            result = {
                "provider": provider,
                "ok": provider_ok,
                "tools": tool_checks,
                **turn_checks,
            }
        except Exception as exc:
            result = {
                "provider": provider,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        summary[provider] = result
        if not result["ok"]:
            failures += 1
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))

    smoke_dir = settings.data_dir / "app" / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = smoke_dir / f"agent-smoke-{stamp}.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"summary: {output.relative_to(REPO_ROOT)}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
