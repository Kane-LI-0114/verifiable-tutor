# ADR-0018: Per-provider thinking policy for tool-calling turns

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-06 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

[ADR-0016](0016-minimal-agent-loop-and-typed-tools.md) introduced the minimal agent loop with a global `thinking.disable_for_tools: true` switch. The switch was chosen because the two chat providers differ: DeepSeek accepts tools in thinking mode while `tool_choice` stays `auto` or `none`, and MiMo documents unstable tool calls in thinking mode unless the previous `reasoning_content` is echoed back. The global switch avoided both problems by turning thinking off for every tool turn, but it also hid model reasoning from the work chain that ADR-0017 now records.

The 2026-11-06 DeepSeek documentation states the constraint precisely: when a request carries `tools`, the `reasoning_content` of all previous turns must be passed back or the API returns 400; `required` and named tool choices are rejected in thinking mode. MiMo's documentation states the same replay requirement for multi-turn tool calls and calls the combination unstable.

The lead asked for the switch to be configured per provider, so DeepSeek can keep thinking with tools while MiMo keeps its safer default.

## Decision

**`thinking.disable_for_tools` is a provider to boolean mapping**, for example:

```yaml
thinking:
  disable_for_tools:
    deepseek: false
    mimo: true
```

The configuration loader requires an entry for every configured provider and rejects unknown provider names, so a typo cannot silently disable the policy.

**The adapter applies the policy per provider.** `_effective_thinking` receives the resolved provider name and forces `off` only when that provider's entry is true. In a DeepSeek thinking turn with tools, the adapter forces `tool_choice` to `auto` when the caller asked for `required` or a named function, because DeepSeek returns 400 for those values in thinking mode; `auto` and `none` pass through. MiMo already forces `auto`.

**The runner and history replay reasoning_content when thinking is active.** Inside a tool loop, every assistant tool-call message carries the reasoning that produced it when the model emitted any. The conversation history also carries `reasoning_content` for prior assistant messages that stored reasoning, so a later request with tools satisfies the provider contract. The work-chain events from ADR-0017 then show that reasoning before the tool calls it preceded.

**Default policy:** DeepSeek `false`, MiMo `true`. The default chat thinking level is still `off`, so the behavior changes only when the user selects a thinking level. MiMo can be opted in, but the operator accepts the provider's instability warning.

**MiMo exposes only Off and On.** The composer offers two choices for MiMo, and the adapter normalizes a stored or requested `low` or `max` to `high`, its enabled value, so the trace and the wire request never claim an effort MiMo does not have. DeepSeek keeps its four levels.

## Consequences

**Positive:**

- Reasoning before tool calls is now visible and persisted for DeepSeek when the user selects thinking, which completes the intent of ADR-0017.
- The provider-specific hazard is expressed in configuration instead of a comment, and a missing provider entry fails at startup rather than silently changing behavior.
- MiMo keeps the conservative default that avoids the reasoning replay hazard.

**Negative:**

- `reasoning_content` replay adds tokens to every request that carries prior reasoning, and a provider change can alter context size.
- The adapter has one more provider-specific branch (`tool_choice` normalization) that must be re-checked when providers change.
- Enabling MiMo thinking with tools remains at the operator's risk; the project does not claim the combination is stable.

**Neutral:**

- The evaluation path keeps thinking off by default, so benchmark runs are deterministic.
- The work-chain schema does not change; this ADR changes what reasoning the loop produces and sends.

## Alternatives considered

**Keep the global switch and never show reasoning with tools.** For: the simplest and safest loop. Against: the lead asked for per-provider configuration and ADR-0017 exists to show reasoning before actions.

**Always enable thinking for both providers.** For: consistent behavior. Against: MiMo documents unstable tool calls and the replay requirement; a default that is unstable is worse than a conservative default.

**Force `tool_choice: auto` for every provider and every tool turn.** For: one less branch. Against: it removes a caller's ability to force a tool on DeepSeek in non-thinking mode, which the adapter supports today.

**Put the policy in a prompt instead of configuration.** For: no config schema change. Against: the provider contract is a wire-level constraint, and a prompt cannot enforce it.

## References

- Agent loop and tools: [ADR-0016](0016-minimal-agent-loop-and-typed-tools.md)
- Ordered work-chain events: [ADR-0017](0017-ordered-work-chain-events.md)
- Provider behavior: [../model-providers.md](../model-providers.md)
- DeepSeek thinking mode and tool calls: https://api-docs.deepseek.com/guides/thinking_mode
- DeepSeek Chat Completions: https://api-docs.deepseek.com/api/create-chat-completion
- MiMo OpenAI-compatible API: https://mimo.mi.com/static/docs/api/chat/openai-api-post.md
- Configuration: [../../config/models.yaml](../../config/models.yaml)
