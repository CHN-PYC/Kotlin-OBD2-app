# Prompt Builder Learning Card

## Purpose

Convert a validated vehicle QA request into a deterministic model request. The
builder prepares model input but does not call a model, perform retrieval, or
parse an answer.

## Input

`VehicleQARequest`, including the user question, vehicle context, and optional
rule diagnosis summary.

## Output

`ChatRequest` containing one system message, one user message, and conservative
generation options.

## Algorithm

1. Export Pydantic models with `model_dump(mode="json", by_alias=True)`.
2. Keep only model-relevant evidence; exclude `session_id` and `top_k`.
3. Serialize the evidence as compact UTF-8 JSON.
4. Add system constraints for grounding, uncertainty, and cautious diagnosis.
5. Use temperature zero and a bounded output-token limit.

## Reason For Selection

Structured JSON preserves field boundaries better than manually formatted prose
and makes prompts reproducible in tests and traces. A separate builder prevents
prompt policy from becoming coupled to HTTP transport or model-provider code.

## Failure Cases

- Passing a Pydantic object directly to `json.dumps` raises a serialization error.
- Ignoring the return values of `model_dump` or `json.dumps` discards conversion.
- Omitting the optional-summary branch breaks requests without rule evidence.
- Weak system constraints allow unsupported or overly certain fault claims.
- Adding unrelated identifiers wastes tokens and can leak internal data.

## Debugging

Inspect message roles, parse the user message back with `json.loads`, and compare
its fields with the original request. Prompt construction failures should be
debugged before sending any request to Ollama.

## Evaluation

Unit-test message order, generation parameters, required evidence fields,
optional `null` handling, excluded control fields, and safety instructions.
Later end-to-end evaluation should separately measure answer grounding.

## Possible Replacement

The manual builder can later be replaced by a versioned template engine or a
framework prompt template. The typed `ChatRequest` boundary should remain stable
so that changing templates does not affect provider implementations.
