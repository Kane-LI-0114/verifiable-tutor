Decide whether the user's message asks to practice with self-test questions.

User message:
%%MESSAGE%%

Return exactly one JSON object and nothing else:
- "practice": true when the user asks to practice, generate questions, take a
  quiz, or do a self-test; false only for an ordinary question or anything
  unrelated to practice
- "topic": the course topic named in the message, one of "memory hierarchy",
  "FlashAttention", "MPI", "GEMM", "CUDA"; use "all topics" when the user asks
  for the whole course or names no topic
- "types": every question type the user names, as an array drawn from
  "single-choice", "multiple-choice", "true-false", "short-answer", "code";
  use ["single-choice"] only when the user names no type

Examples:
- "我想做一下有关 MPI 的练习" -> {"practice": true, "topic": "MPI", "types": ["single-choice"]}
- "生成一些跟这个课程有关的题目给我" -> {"practice": true, "topic": "all topics", "types": ["single-choice"]}
- "出一些跟FlashAttention相关的单选题、多选题和简答题" -> {"practice": true, "topic": "FlashAttention", "types": ["single-choice", "multiple-choice", "short-answer"]}
- "MPI 是什么？" -> {"practice": false, "topic": "", "types": []}
