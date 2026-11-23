# Self-test blind annotation template

Procedure from benchmark-protocol.md section 3 step 4. Fill one record per
question into `generation/<run-id>/annotations.jsonl`.

## Steps

1. **De-identify.** Merge the A and B question sets, give each question a random
   id, and hide the `source` field. Keep the id-to-source mapping separate.
2. **Annotate independently.** Two annotators mark each question without seeing
   the other's marks or the source.
3. **Join.** Compare, resolve disagreements by discussion, then restore `source`.

## Per-question fields

| Field | Type | How to fill |
|---|---|---|
| `question_id` | string | The de-identified question id |
| `knowledge_points` | array of string | Covered points, mapped to the course knowledge-point list (`knowledge_points.yaml`) |
| `valid` | boolean | True only when answerable, reference correct, no duplicate, no assignment leak |
| `validity_notes` | array of string | Reasons when `valid` is false; empty otherwise |
| `difficulty` | string | `low` / `medium` / `high` |
| `annotator` | string | Your de-identified annotator id, e.g. `dev-1` / `dev-2` |
| `verified_max_score` | number | Confirmed maximum score for the question |

## Example

```json
{"question_id":"a-001","knowledge_points":["cache hierarchy","latency"],"valid":true,"validity_notes":[],"difficulty":"low","annotator":"dev-1","verified_max_score":1}
```

## What to check when marking `valid`

- Answerable: the question can be answered from the reference answer alone.
- Reference answer correct: no factual error.
- No duplicate: not a near-copy of another question in the set.
- No assignment leak: does not reveal a complete solution to a current assignment.
