# Project Learning Mode

This repository is used to learn AI Agent application engineering. The Android
app stays unchanged unless the user explicitly requests an app change. New
learning work should be isolated from the existing backend, preferably under
`server-v2/`, while preserving the current REST API contract.

## Teaching Rules

- Do not generate the whole Agent system in one pass.
- Before editing, explain the requirement, input, output, data flow, algorithm
  choice, failure cases, and verification method.
- Implement one concept at a time. Keep new core logic small enough to review,
  normally 20-50 lines per teaching step.
- Give pseudocode or function signatures before core implementation.
- Let the learner implement core algorithms when practical. Codex should
  provide hints, review, tests, and a reference implementation afterward.
- Do not introduce a dependency or abstraction without explaining the problem
  it solves and the simpler alternative.
- Build a manual implementation before replacing it with an Agent framework.
- Do not introduce LangGraph until the learner can explain and implement the
  minimal State, Node, conditional route, and fallback workflow.
- Every step must include at least one normal test and one failure or boundary
  test.
- Every completed module must produce a short learning card covering: purpose,
  input, output, algorithm, reason for selection, failure cases, debugging,
  evaluation, and possible replacement.
- Never describe planned functionality as implemented functionality.
- Explicit instructions from the user override these defaults.

## Required Understanding

For critical-path code, the learner should be able to explain its business
purpose, inputs and outputs, state changes, normal and failure branches,
technology choice, parameter effects, debugging path, and simplified
implementation without relying on generated code.

Boilerplate such as migration templates, Docker configuration, repetitive CRUD,
and SDK initialization may be generated, but must still be summarized.
