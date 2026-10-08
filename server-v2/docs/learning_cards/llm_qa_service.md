# LLM QA Service Learning Card

## Purpose

Orchestrate prompt construction, model generation, output acceptance, and a
deterministic rule fallback for one vehicle question.

## Input

A validated `VehicleQARequest` plus injected `ChatModel`, prompt builder, and
fallback service dependencies.

## Output

A `VehicleQAResponse` in `llm_only` mode after accepted generation, or a safe
rule-based response in `llm_call_failed` mode after provider or truncation
failure.

## Algorithm

1. Build a rule-based baseline response.
2. Convert the request into a typed chat request.
3. Await one model call; retry behavior remains inside the model decorator.
4. Catch only known provider errors and return the baseline with failure trace.
5. Reject any result whose finish reason is not `stop`.
6. Parse and validate the model content as a structured vehicle answer.
7. On success, replace the baseline answer, findings, recommendations, and trace
   while retaining deterministic control fields.

## Reason For Selection

The service owns business orchestration while the provider owns HTTP and the
retry decorator owns retry policy. A deterministic baseline keeps the API usable
when the optional model dependency fails. The mode is `llm_only`, not `llm_rag`,
because retrieval has not been implemented yet.

## Failure Cases

- Provider timeout, connection failure, server error, or invalid response.
- Truncated generation such as `finish_reason=length`.
- Invalid JSON or output that violates the generated-answer schema.
- Missing rule evidence, which lowers successful output confidence.
- Unexpected programming errors, which are deliberately not hidden by a broad
  `except Exception` fallback.

## Debugging

Read `answer_mode` first, then inspect ordered `agent_trace` steps. Provider
failure details contain the normalized error code; truncation details contain
the finish reason. Test the service with a stub model before using Ollama.

## Evaluation

Measure model-call success rate, fallback rate by error code, truncation rate,
latency, and grounded-answer quality. Do not count a fallback response as an LLM
success merely because the HTTP endpoint returned 200.

## Possible Replacement

The manual conditional flow can later become explicit Agent workflow nodes or a
LangGraph graph. The `VehicleQAService` protocol and typed response contract can
remain unchanged.
