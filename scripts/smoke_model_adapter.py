#!/usr/bin/env python3
"""Live smoke test for the unified model adapter.

This script makes real, minimal-cost calls to DeepSeek and Xiaomi MiMo using
the keys in .env. It is not part of the pytest suite.

Run with:

    .venv/bin/python scripts/smoke_model_adapter.py

Every step prints one line with provider, model, latency, and a short result.
A failed step is reported and the script exits non-zero at the end.
"""

from __future__ import annotations

import base64
import io
import struct
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from verifiable_tutor.llm.adapter import ModelAdapter  # noqa: E402
from verifiable_tutor.llm.config import load_model_config  # noqa: E402

# A 1x1 red PNG, small enough to stay inside one image token bucket.
RED_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def make_wav_silence(seconds: float = 1.0, rate: int = 16000) -> bytes:
    """Build a mono 16-bit PCM WAV of silence for the ASR smoke call."""

    frames = int(seconds * rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * frames)
    return buffer.getvalue()


def png_size(png: bytes) -> tuple[int, int]:
    width, height = struct.unpack(">II", png[16:24])
    return width, height


def run_step(name: str, fn) -> bool:
    started = time.monotonic()
    try:
        detail = fn()
    except Exception as exc:  # noqa: BLE001 - smoke reports every failure
        elapsed = time.monotonic() - started
        print(f"[FAIL] {name} ({elapsed:.2f}s): {type(exc).__name__}: {exc}")
        return False
    elapsed = time.monotonic() - started
    print(f"[ OK ] {name} ({elapsed:.2f}s): {detail}")
    return True


def main() -> int:
    env_file = ROOT / ".env"
    resolved = load_model_config(ROOT / "config" / "models.yaml", env_file=env_file)
    # The smoke script must exercise the real network, so it bypasses the
    # response cache; cache behavior is covered by tests/llm/test_cache.py.
    resolved.config.cache.enabled = False
    adapter = ModelAdapter(resolved)
    failures: list[str] = []

    def deepseek_chat() -> str:
        result = adapter.chat(
            [{"role": "user", "content": "Reply with the single word: OK"}],
            thinking="off",
            max_output_tokens=16,
        )
        return f"{result.provider}/{result.model} text={result.text!r} finish={result.finish_reason}"

    def deepseek_stream() -> str:
        parts: list[str] = []
        for event in adapter.chat_stream(
            [{"role": "user", "content": "Count from 1 to 3, comma separated."}],
            thinking="off",
            max_output_tokens=24,
        ):
            if event.kind == "text" and event.text:
                parts.append(event.text)
        return f"deepseek/deepseek-flash streamed={''.join(parts)!r}"

    def deepseek_image() -> str:
        width, height = png_size(RED_PIXEL_PNG)
        data_url = "data:image/png;base64," + base64.b64encode(RED_PIXEL_PNG).decode("ascii")
        result = adapter.chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is the dominant color? One word."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            thinking="off",
            max_output_tokens=16,
        )
        return f"image={width}x{height} text={result.text!r}"

    def deepseek_search() -> str:
        results = adapter.search("TACC HKUST Slurm cluster", count=3, need_content=False)
        titles = "; ".join(result.title for result in results) or "(no results)"
        return f"results={len(results)} titles={titles}"

    def deepseek_fetch() -> str:
        page = adapter.fetch("https://example.com")
        return f"title={page.title!r} markdown_chars={len(page.content)}"

    def mimo_chat(tier: str) -> str:
        provider, model = "mimo", tier
        result = adapter.chat(
            [{"role": "user", "content": "Reply with the single word: OK"}],
            provider=provider,
            tier=tier,
            thinking="off",
            max_output_tokens=16,
        )
        return f"{result.provider}/{result.model} text={result.text!r} finish={result.finish_reason}"

    def mimo_asr() -> str:
        audio = make_wav_silence()
        result = adapter.transcribe(audio, mime="audio/wav", language="auto")
        return f"{result.model} text={result.text!r} seconds={result.seconds}"

    def mimo_audio_file() -> str:
        audio = make_wav_silence(0.5)
        data_url = "data:audio/wav;base64," + base64.b64encode(audio).decode("ascii")
        result = adapter.chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "input_audio": {"data": data_url}},
                        {"type": "text", "text": "Describe this audio in one word."},
                    ],
                }
            ],
            provider="mimo",
            tier="flash",
            thinking="off",
            max_output_tokens=16,
        )
        return f"{result.provider}/{result.model} text={result.text!r}"

    def mimo_tts() -> str:
        result = adapter.speak("Hello from the verifiable tutor.", format="wav")
        return f"{result.model} voice={result.voice} format={result.format} audio_bytes={len(result.audio)}"

    steps = [
        ("deepseek chat", deepseek_chat),
        ("deepseek stream", deepseek_stream),
        ("deepseek image", deepseek_image),
        ("deepseek search", deepseek_search),
        ("deepseek fetch", deepseek_fetch),
        ("mimo flash chat", lambda: mimo_chat("flash")),
        ("mimo pro chat", lambda: mimo_chat("pro")),
        ("mimo asr", mimo_asr),
        ("mimo audio file", mimo_audio_file),
        ("mimo tts", mimo_tts),
    ]

    for name, fn in steps:
        if not run_step(name, fn):
            failures.append(name)

    print()
    if failures:
        print(f"FAILED steps: {', '.join(failures)}")
        return 1
    print("All smoke steps passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
