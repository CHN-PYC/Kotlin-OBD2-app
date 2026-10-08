# Structured Model Output Learning Card

## Purpose

Turn untrusted model text into a validated domain object before business code
uses any generated field.

## Input

A `ChatResult` whose `content` should contain one plain JSON object.

## Output

A validated `GeneratedVehicleAnswer` containing `answer`, `findings`, and
`recommendations`.

## Algorithm

1. Ask the model for an exact JSON object without Markdown fences.
2. Decode `ChatResult.content` with the standard JSON parser.
3. Validate the decoded value with a strict Pydantic schema.
4. Map JSON and schema failures to `InvalidModelResponseError` while preserving
   the original exception as its cause.

## Reason For Selection

JSON provides explicit field boundaries and Pydantic enforces required fields,
limits, and unknown-field rejection. Regex extraction is fragile for nesting,
escaping, and malformed output. Severity, confidence, and workflow mode remain
deterministic server decisions rather than model claims.

## Failure Cases

- Malformed or truncated JSON.
- Missing or blank `answer`.
- Unknown fields caused by schema drift or spelling mistakes.
- Excessive list sizes.
- Markdown code fences around otherwise valid JSON.

## Debugging

Log or trace the provider, model, normalized error code, and a safely truncated
representation of the raw response. Inspect `error.__cause__` to distinguish a
JSON decoding failure from a Pydantic validation failure.

## Evaluation

Track parse-success rate, validation failures by field, schema-drift incidents,
and fallback rate. Include malformed JSON, missing fields, extra fields, blank
text, and boundary-size cases in tests.

## Possible Replacement

A provider-native structured-output or JSON-schema feature can reduce formatting
errors. Validation must remain at the application boundary even when a provider
claims schema compliance.
