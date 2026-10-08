# Remaining Engineering Gaps

This document separates implemented behavior from the next production concerns.

## Implemented Now

- Deterministic terminology normalization and latest-turn reference resolution.
- Original and rewritten queries retained separately in the API response and trace.
- Request context priority: current telemetry, retrieved evidence, recent history.
- Complete-unit context selection under a serialized-character budget.
- Redis List short-term memory with transactional append, bounded length, and TTL.
- Session-key hashing, explicit memory deletion, and non-critical Redis fallback.
- Unit, API multi-turn, retrieval, fallback, and real Redis smoke verification.
- Request-level cooperative async deadline and rule fallback trace.
- Process-local chat circuit breaker with one recovery probe and stale-result protection.
- Zero history-turn limit now excludes all history; turn timestamps use server time.

## P0: Correctness And Safety

1. **Tenant ownership**: bind `session_id` to an authenticated user/vehicle. A global
   API key plus a caller-provided session ID is not multi-tenant authorization.
2. **Exact token budget**: replace character estimation with the selected generation
   model tokenizer and reserve space for output and provider-added message tokens.
3. **Multi-turn evaluation**: label reference-resolution, topic-switch, stale-history,
   and adversarial-history cases. Single-turn retrieval metrics are insufficient.
4. **Prompt-injection boundary**: treat stored history and retrieved text as untrusted
   data, add injection tests, and prevent either from changing system policy.
5. **Retention/privacy**: document stored fields, deletion guarantees, audit access,
   Redis authentication/TLS, backups, and environment-specific retention periods.

## P1: Reliability And Observability

1. Extend the implemented chat circuit breaker to Embedding/Qdrant if operational
   measurements justify it. Add shorter Redis operation budgets; a Redis outage can
   currently consume the total request budget. The async deadline cannot kill local
   inference threads or undo completed writes.
2. Emit metrics for rewrite rules, history turns selected, context occupancy, Redis
   p95 latency, memory fallback, retrieval fallback, and model truncation.
3. Add idempotency/request IDs. Concurrent requests for one session currently append
   atomically but their semantic ordering depends on completion order.
4. Add Redis health/readiness, authentication, persistence restore tests, and a
   production deployment policy; one local container is not high availability.
5. Add generation faithfulness and answer-fact coverage evaluation in addition to
   retrieval Hit@K/MRR.

## P2: Capability Expansion

1. Summarize old turns before eviction, with source-turn IDs and summary versioning.
2. Store long-term vehicle/user facts separately from short-term dialogue, requiring
   explicit consent and update/delete rules.
3. Add metadata filtering for vehicle model, engine, language, document version, and
   diagnostic topic when labels are reliable.
4. Add clarification questions when required vehicle facts are missing instead of
   always retrieving and generating immediately.
5. Introduce bounded model-selected tool calling only after call-count, duplicate-call,
   deadline, and cost controls are implemented.

## Framework Decision

LangChain is not required for these gaps. LangGraph becomes useful after adding
pause/resume clarification, durable checkpoints, human approval, or bounded tool
loops. Until then, the explicit workflow remains smaller and easier to audit.
