import json
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
OUT = Path(r"D:\2026-Fall\6000V\verifiable-tutor-main\.vt-tmp\eval")
OUT.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    "根据 Lecture 2，memory wall 具体指什么？对系统性能的影响是什么？",
    "Lecture 2 里 DRAM 和 SRAM 在速度、密度、成本上的区别是什么？",
    "什么是时间局部性和空间局部性？各举一个例子。",
    "GPU 内存层次里寄存器和共享内存的角色分别是什么？bank conflict 是什么？",
    "Lecture 2 里 HBM/GDDR 和 CXL 各解决什么问题？",
    "FlashAttention 的核心思想是什么？为什么能避免物化 attention 矩阵？",
    "什么是 online softmax？它和普通 softmax 的区别是什么？",
    "FlashAttention 里的 tiled GEMM 是怎么用 shared memory 的？",
    "attention operator 里 QK^T / sqrt(d_k) 中的 sqrt(d_k) 是什么作用？",
    "stable softmax 为什么要减去最大值？",
    "FlashAttention 的 shared-memory tiling 和 Lecture 2 讲的 GPU shared memory / bank conflict 有什么关系？",
    "FlashAttention 为什么要避免物化 N×N 的 attention 矩阵？这和 Lecture 2 的 memory wall 怎么联系起来？",
    "FlashAttention 用到的 online softmax 需要什么样的内存访问模式？和 Lecture 2 的 locality 概念有什么关系？",
    "MPI 里 point-to-point 和 collective communication 的区别是什么？",
    "GEMM 里 shared-memory tiling 如何减少 global memory 访问？",
]


def parse_sse(text: str):
    answer = ""
    sources = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data: "):
            continue
        try:
            payload = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "text-delta":
            answer += payload.get("delta", "")
        elif payload.get("type") == "data-sources":
            sources = (payload.get("data") or {}).get("sources", [])
    return answer, sources


def main():
    with httpx.Client(timeout=240.0) as c:
        r = c.post(BASE + "/api/auth/login", json={"email": "ytianbn@connect.ust.hk", "password": "vt-demo-2026"})
        print("login", r.status_code)

        # Part 2B: answer the 15 questions
        answers = []
        for i, q in enumerate(QUESTIONS, 1):
            t0 = time.time()
            r = c.post(BASE + "/api/chat", json={"message": q})
            answer, sources = parse_sse(r.text)
            answers.append({"index": i, "question": q, "answer": answer, "sources": sources})
            print(f"[2B {i}/15] {time.time()-t0:.1f}s len={len(answer)} sources={len(sources)}", flush=True)
        (OUT / "part2b_answers.jsonl").write_text(
            "\n".join(json.dumps(a, ensure_ascii=False) for a in answers), encoding="utf-8"
        )

        # Part 3A: generate 10 single-choice questions for FlashAttention
        t0 = time.time()
        r = c.post(BASE + "/api/practice/generate", json={"topic": "FlashAttention", "types": ["single-choice"]})
        gen = r.json()
        (OUT / "part3a_questions.json").write_text(json.dumps(gen, ensure_ascii=False, indent=2), encoding="utf-8")
        qs = gen.get("questions", [])
        print(f"[3A] {time.time()-t0:.1f}s questions={len(qs)}")
        for q in qs:
            print("  -", q.get("type"), "|", q.get("topic"), "| kp:", q.get("knowledge_points"))

    print("DONE ->", OUT)


if __name__ == "__main__":
    main()
