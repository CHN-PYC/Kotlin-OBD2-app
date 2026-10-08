# Model Provider Learning Card

## Purpose

Expose one `ChatModel` contract to the application while isolating Ollama HTTP details,
configuration, response parsing, and retry policy.

## Input And Output

- Input: ordered `ChatMessage` values plus `temperature` and `max_output_tokens`.
- Output: normalized content, provider identity, actual model identity, finish reason, and
  input/output token counts.

## Workflow

`Settings -> create_chat_model -> RetryingChatModel -> OllamaChatModel -> POST /api/chat`

The adapter maps `max_output_tokens` to Ollama `num_predict`, disables streaming and
thinking, validates the response, and returns `ChatResult`. The retry wrapper retries only
errors whose stable type declares `retryable = True`, using bounded exponential backoff.

## Why This Design

- `Protocol` keeps Agent code independent of Ollama and supports fake providers in tests.
- A factory centralizes object assembly and environment-specific parameters.
- Typed errors keep transport exceptions out of Agent routing logic.
- A shared async HTTP client can be injected for connection pooling and lifecycle control.

## Failure Cases

- Missing model configuration: fail fast, do not retry.
- Timeout, connection failure, or provider 5xx: bounded retry.
- Provider 4xx or invalid response: do not perform transport-level retry.
- `finish_reason=length`: result is truncated and must not be treated as a complete answer.

## Debugging

Check the error code, provider, configured model, HTTP status class, finish reason, token
counts, and retry attempt count. Do not log prompts, raw vehicle context, API keys, or raw
model responses by default.

## Evaluation

Unit tests cover payload mapping, response normalization, error mapping, retry limits,
backoff timing, configuration validation, and factory composition. A local `qwen3:4b`
smoke test confirmed the HTTP integration and exposed truncated thinking output at a
64-token budget.

## Possible Replacements

Add `OpenAIChatModel` or another adapter that satisfies `ChatModel`; keep the Agent,
request types, retry wrapper, and most tests unchanged. LangChain can be integrated later
through an adapter instead of replacing the domain contract.
