# Learning Card: Query, Context, And Session Memory

## Purpose

Turn independent QA calls into bounded multi-turn diagnosis without allowing stale
history to override current telemetry or retrieved evidence.

## Data Flow

```text
session_id -> Redis LRANGE -> recent turns
question + recent turn -> deterministic query rewrite
rewritten query -> hybrid retrieval -> Evidence Gate
current vehicle context -> evidence -> recent history -> context selection
LLM/fallback result -> Redis transaction: RPUSH + LTRIM + EXPIRE
```

## Query Rewrite

The rewriter normalizes domain aliases such as water temperature to `ECT` and air
flow meter to `MAF`. Referential questions such as “这个怎么检查” use only the most
recent turn. Original and rewritten queries remain separate for trace and evaluation.

This first version is deterministic. It is cheap, reproducible, and cannot invent a
new vehicle fact. Its limitation is weak handling of complex ellipsis and intent.

## Context Policy

Mandatory current-request data is admitted first. Complete evidence chunks are added
in rank order, then the newest history turns that fit. A chunk or turn is never cut in
half. If mandatory data alone exceeds the budget, the workflow falls back.

The current budget uses serialized characters, not exact tokens. Before production,
use the selected generation model's tokenizer or reserve a conservative token margin.

## Redis Memory

Each session is a Redis List under a SHA-256-derived key. The raw session ID is not
placed in the Redis key. Append, trim, and TTL refresh run in one transaction. Current
defaults retain 10 exchanges for 30 minutes. `DELETE /qa/sessions/{session_id}/memory`
provides explicit removal.

Redis failure does not block diagnosis: the workflow continues with empty history,
and append failure does not change the already computed answer.

## What This Is Not

- Not long-term user memory or a user profile.
- Not a replacement for Room vehicle Session records.
- Not Qdrant knowledge storage.
- Not durable Agent checkpoint/resume.
- Not authorization: a future multi-user service must bind sessions to user/tenant IDs.

## Evaluation

Measure reference-resolution accuracy, retrieval quality before/after rewrite, history
usage rate, context occupancy, Redis p95 latency, memory fallback rate, and stale-history
regressions. Maintain multi-turn test cases rather than evaluating only single queries.
