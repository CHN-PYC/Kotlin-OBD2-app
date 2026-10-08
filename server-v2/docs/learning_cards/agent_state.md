# Agent State Learning Card

## Purpose

Hold the typed inputs, intermediate products, execution phase, failure reason,
and final output for one Agent run.

## Input

A validated `VehicleQARequest`. Later nodes add a rule baseline, chat request,
provider result, parsed answer, trace steps, and final response.

## Output

A sequence of `VehicleAgentState` snapshots ending in `completed` or `fallback`.

## Algorithm

Start in `received`. Each node reads one state and returns a copied state with
its output, next phase, and appended trace. The intended normal progression is
`received -> baseline_prepared -> prompt_built -> model_generated -> output_parsed -> completed`;
recoverable failures route to `fallback`.

## Reason For Selection

A typed Pydantic model makes intermediate data explicit and testable before a
workflow framework is introduced. Snapshot-style updates preserve earlier state
for debugging and make node inputs and outputs easier to reason about.

## Failure Cases

- A phase value does not match its declared meaning.
- An intermediate field uses the request type where a response type is required.
- A node writes a result but forgets to advance the phase or append trace.
- Mutable trace data is reused instead of creating a new list.
- Application clients or cross-session history are incorrectly stored in run state.

## Debugging

Inspect `phase`, then `failure_code`, then ordered `trace`. Compare consecutive
snapshots to identify the node that introduced an invalid value. A passing test
suite still requires semantic review of field names and types.

## Evaluation

Test initial defaults, legal snapshots, rejected unknown fields, independent
trace lists, exact enum values, and the declared type of every intermediate.
Later workflow tests should cover every conditional route.

## Possible Replacement

The Pydantic state can later be represented as a LangGraph state schema or a
dataclass. Its business fields and phase meanings should remain framework-neutral.
