# ADR-0006: Same-model retries without automatic cross-model fallback

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-29 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The deployed service must not switch models behind the user's back. A fallback from the selected model to a different model makes the answer's origin unclear, changes cost and quality without consent, and hides provider failures. The service should instead wait for the selected model, retry it internally, and, when the retries are exhausted, show a timeout or unavailable message so the user can decide when to retry. [ADR-0005](0005-external-model-apis-as-primary.md) described a fallback from the chat role to MiMo; this record replaces that behavior.

## Decision

- The provider and tier selected for the request are authoritative for the whole request. The adapter never calls a different provider or tier after a failure.
- Transient failures (timeouts, connection errors, 408, 409, 429, and 5xx) retry the same request on the same model up to `defaults.max_retries`, which is two retries and therefore three attempts with the current configuration.
- After the last failed attempt the adapter raises `ModelResponseError` with a stable `reason` (`timeout` or `unavailable`), the attempt count, and a user-facing `user_message`.
- The service shows that copy and waits for the user to retry. It does not retry in the background and does not switch models.
- Non-retryable errors (400, 401, 403, 422) keep their `ProviderAPIError` status and are not presented as timeouts.
- The response cache stores only successful responses, so an error never becomes a cached answer.
- Streaming retries only before the first event. After partial output the adapter raises the same error instead of replaying a partial answer.

## Consequences

**Positive:**

- Every answer stays attributable to the model the user selected.
- Cost and quality change only when the user or the config changes the model.
- Failure copy is predictable, and the cache cannot hide an outage behind a stale success.
- The user controls when a paid retry happens.

**Negative:**

- A provider outage now fails the request instead of silently using the other provider.
- The user must retry manually after the retry budget is exhausted.
- The retry budget multiplies the worst-case wait by the attempt count.

**Follow-up:**

- The UI maps `reason` to localized copy and exposes a retry action; it should not show a raw provider error.
- Revisit the retry count and any backoff once real latency is measured on TACC.

## Alternatives considered

**Automatic cross-model fallback (the previous behaviour).** For: a request succeeds when one provider has an outage or a bad key. Against: the answer's origin becomes unclear, cost and quality change without the user's consent, and the failure is hidden; the lead replaced it with same-model retries.

**Retry with exponential backoff and `Retry-After` handling.** For: gentler on rate limits and provider-side congestion. Against: the timeout budget is 60 seconds per call and the worst case already multiplies by the attempt count, so whether backoff pays is unmeasured. Kept as a follow-up once real latency is measured, not part of the first version.

**Prompt-level retry (ask the model to answer again).** For: no transport-level machinery. Against: it does not address timeouts, connection errors, or provider failures, and it adds cost; not chosen.

**No retries.** For: the fastest failure and no multiplied wait. Against: transient 408, 429, and 5xx responses would surface as failures without a second chance; not chosen.

## References

- Retry and timeout defaults: [../../config/models.yaml](../../config/models.yaml)
- Retry implementation: [../../src/verifiable_tutor/llm/adapter.py](../../src/verifiable_tutor/llm/adapter.py)
- Retry tests: [../../tests/llm/test_chat.py](../../tests/llm/test_chat.py) and [../../tests/llm/test_stream.py](../../tests/llm/test_stream.py)
- Replaced decision: [ADR-0005](0005-external-model-apis-as-primary.md)
- Model provider notes: [../model-providers.md](../model-providers.md)
