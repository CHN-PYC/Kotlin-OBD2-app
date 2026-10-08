# Learning Card: Agent Tool Registry

## Purpose

Tools give an Agent a narrow capability with a stable contract. The Registry is a
whitelist and dispatcher; it is not a planner and does not itself ask an LLM which
tool to call.

## Contract

Each `AgentTool` declares a unique name, description, Pydantic input model, Pydantic
output model, timeout, and async handler. `definition()` produces a function schema
that can later be sent to a compatible model.

```text
tool name + raw arguments
  -> whitelist lookup
  -> input schema validation
  -> timeout-bounded execution
  -> output schema validation
  -> typed result or sanitized ToolRegistryError
```

## Registered Tools

- `search_vehicle_knowledge`: real hybrid RAG retrieval and current Workflow use.
- `lookup_pid_definition`: deterministic PID terminology and units.
- `interpret_dtc`: validates DTC shape and classifies it without claiming a bad part.
- `analyze_session_signals`: applies explicit screening heuristics to SessionSummary.

## Why These Tools

They are read-only, deterministic or evidence-producing, easy to validate, and
useful for vehicle questions. They cannot modify an index, execute shell commands,
call arbitrary URLs, alter Agent state, or suppress fallback.

Evidence Gate and fallback are not tools because allowing the model to invoke or
skip its own guardrails would invert the trust boundary. Prompt construction and
state transitions are orchestration, not external capabilities.

## Failure Cases

- Unknown name: `UnknownToolError` before any handler runs.
- Duplicate registration: startup/configuration failure.
- Missing or malformed argument: `ToolInputValidationError` backed by Pydantic.
- Invalid handler result: `ToolOutputValidationError`.
- Deadline exceeded: `ToolTimeoutError`; the coroutine is cancelled by `wait_for`.
- Embedding/Qdrant failure: provider error reaches the retrieval node and triggers
  the existing rule fallback branch.

## Debugging And Evaluation

Record tool name, duration, status, error code, and result count, never secrets or
raw private vehicle data. Evaluate argument-valid rate, tool success rate, p95
latency, fallback rate, unnecessary-call rate, and end-task correctness.

The current workflow calls retrieval deterministically. Introduce model-selected
tool calling only when questions genuinely require conditional tool choice, then add
allowed-tool sets, maximum call count, repeated-call detection, and per-tool budgets.
