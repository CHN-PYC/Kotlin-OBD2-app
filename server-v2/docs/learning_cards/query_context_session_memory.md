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

### Fixed: recursive rewrite growth

The first version built `关于上一轮 {previous rewritten_query}；当前问题：...` and then
cut at 500 characters. The derived query was stored in memory and fed back as input,
so each follow-up nested one more layer, and the cut removed the current question.

Current rules:

1. **Raw facts only.** History contributes original `question` text, never a stored
   `rewritten_query`. Derived output stays for trace/evaluation and never feeds back.
2. **Topic anchor.** A follow-up (referential word or <= 6 characters) uses the most
   recent self-contained question among retained turns, so chains such as
   "这个呢 -> 它严重吗 -> 那个要换吗" keep the original topic. A self-contained
   question switches topic and carries no history.
3. **Priority composition.** Current question first, then terms/DTC, then
   `上文话题`. Only lower-priority parts are truncated to the 500-character budget.

Failure cases: a long new question with no referential word but implicit ellipsis is
treated as a topic switch; a short self-contained question (<= 6 characters) is
treated as a follow-up. Both need labeled multi-turn cases to measure. Old Redis
turns with grown `rewritten_query` are harmless because they are no longer read.

Enterprise next steps, not implemented: retrieve with both original and rewritten
queries and fuse with RRF so a bad rewrite cannot remove good results; add an
LLM condense-question rewriter behind validation (must keep current entities,
length bound, timeout, deterministic fallback); store structured slots (DTC, PID,
component) per turn instead of free text; gate any change on multi-turn Hit@K.

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
