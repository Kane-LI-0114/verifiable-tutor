#!/usr/bin/env python3
"""Recognition-only probe: one page through the vLLM OpenAI endpoint.

Uses only the public environment (openai client), no project-layer packages, so
it still produces evidence when the PaddleOCR client stack fails to import.

Usage:
  run_proot "$PUBLIC_ROOT/vllm-env/bin/python" recognition_probe.py \
      --image page.png --server-url http://127.0.0.1:8000/v1 \
      --model PaddleOCR-VL-1.6-0.9B --out probe.json
"""

import argparse
import base64
import json
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--server-url", required=True)
    parser.add_argument("--model", default="PaddleOCR-VL-1.6-0.9B")
    parser.add_argument("--prompt", default="OCR:")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    from openai import OpenAI  # noqa: PLC0415

    started = time.time()
    record = {"schema": "vt-recognition-probe/1", "server_url": args.server_url, "model": args.model}
    try:
        client = OpenAI(base_url=args.server_url, api_key="EMPTY", timeout=600)
        with open(args.image, "rb") as handle:
            image_b64 = base64.b64encode(handle.read()).decode("ascii")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    {"type": "text", "text": args.prompt},
                ],
            }
        ]
        response = client.chat.completions.create(
            model=args.model,
            messages=messages,
            temperature=0.0,
            max_tokens=args.max_tokens,
        )
        content = response.choices[0].message.content or ""
        record.update(
            {
                "ok": True,
                "seconds": round(time.time() - started, 3),
                "chars": len(content),
                "text_head": content[:600],
                "usage": response.usage.model_dump() if getattr(response, "usage", None) else None,
                "served_id": response.model,
            }
        )
        print(f"[probe] ok {record['seconds']}s chars={len(content)}", flush=True)
        print(f"[probe] text: {content[:300]!r}", flush=True)
    except Exception as exc:  # noqa: BLE001
        record.update({"ok": False, "seconds": round(time.time() - started, 3), "error": f"{type(exc).__name__}: {exc}"})
        print(f"[probe] FAILED: {record['error']}", flush=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    return 0 if record.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
