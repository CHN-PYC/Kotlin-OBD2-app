# Vehicle Diagnostic Agent Server V2

`server-v2` is the manually assembled AI backend for the existing Android OBD-II
application. It keeps the Android REST contract stable while making every Agent
step explicit, testable, and replaceable.

## Implemented Architecture

```text
Android POST /qa/vehicle
  -> optional Bearer API-key authentication
  -> Pydantic request validation
  -> request deadline (60 seconds by default)
  -> load bounded Session memory (Redis TTL)
  -> deterministic rule baseline
  -> deterministic query rewrite
  -> whitelisted ToolRegistry with Pydantic argument validation
  -> query embedding (Ollama bge-m3, 1024 dimensions)
  -> Qdrant cosine retrieval + in-memory BM25 lexical retrieval
  -> reciprocal-rank fusion (RRF)
  -> configurable FastEmbed Cross-Encoder rerank (hybrid-order fallback)
  -> evidence gate
  -> structured prompt
  -> process-local circuit breaker -> bounded retries -> chat model
  -> JSON parsing and schema validation
  -> response or rule fallback
  -> append final exchange to Session memory
  -> answer_mode + confidence + agent_trace
```

This is a controlled workflow rather than an unrestricted ReAct loop. Retrieval,
gating, generation, parsing, and fallback are deterministic nodes; the LLM only
generates the diagnosis text from accepted evidence.

## Technology Choices

| Component | Choice | Reason |
|---|---|---|
| API | FastAPI + Pydantic v2 | Async I/O and typed request/response boundaries |
| Chat model | Provider adapter | Switch between Ollama and OpenAI-compatible APIs |
| Embedding | Ollama `bge-m3` | Chinese/English semantic retrieval; 1024-d dense vector |
| Vector storage | Qdrant | Persistence, payload metadata, CRUD, later filtering |
| Test store | In-memory cosine store | Fast deterministic unit tests without infrastructure |
| Retrieval | BGE-M3 dense + BM25 + RRF | Semantic recall plus exact PID/DTC matching without mixing incompatible score scales |
| Reranking | FastEmbed + `BAAI/bge-reranker-base` | CPU ONNX Cross-Encoder for Chinese/English query-document scoring |
| Workflow | Explicit State/Node routing | Easy to debug, trace, test, and explain in interviews |
| Tools | Async whitelist registry + Pydantic schemas | Reject unknown tools, missing parameters, invalid outputs, and timeouts |
| Session memory | Redis List + TTL | Atomic append/trim/expire, bounded recent turns, explicit deletion |
| Query rewrite | Deterministic terminology/reference rules | Explainable rewrite without another model call |
| Context | Priority-based complete-unit selection | Keep current telemetry, then evidence, then recent history under a character budget |
| Fallback | Rule-derived response | Conservative result when retrieval/model/output fails |

Qdrant is a vector database service. The Python package is its client SDK; the
database process runs in Docker. It is not the embedding model and does not create
vectors.

## Registered Agent Tools

| Tool | Input | Output | Current use |
|---|---|---|---|
| `search_vehicle_knowledge` | query, Top-K | typed evidence chunks | Called by the retrieval node |
| `lookup_pid_definition` | PID names | definitions, units, unknown names | Available to a future bounded planner |
| `interpret_dtc` | validated five-character DTC | system, family, conservative note | Available to a future bounded planner |
| `analyze_session_signals` | typed session summary | threshold observations and limitations | Available to a future bounded planner |

The registry emits function schemas compatible with model tool definitions, but the
current workflow does not let the LLM choose arbitrary calls. The server dispatches
the knowledge tool deterministically. Evidence Gate, fallback, authentication,
prompt construction, state transitions, index mutation, and external side effects
are deliberately not model-callable tools; they are the safety control plane.

## Prerequisites

- Python 3.12 and `uv`
- Ollama
- Docker Desktop

One-time model and dependency setup:

```powershell
ollama pull bge-m3
ollama pull qwen3:4b
cd server-v2
uv sync --dev
Copy-Item .env.example .env
```

Set `VEHICLE_AGENT_OLLAMA_CHAT_MODEL=qwen3:4b` in `.env` for local generation,
or set `MODEL_PROVIDER=openai_compatible` with the prefixed `LLM_BASE_URL`,
`LLM_MODEL`, and `LLM_API_KEY` settings. A blank chat model intentionally uses only
the rule service. The example selects Qdrant because ingestion and API processes
cannot share an in-memory index. Unit tests use the memory implementation.

Do not commit `.env`. The Android service API key and the upstream LLM API key are
different credentials.

## Environment

The active local RAG settings are:

```dotenv
VEHICLE_AGENT_OLLAMA_EMBEDDING_MODEL=bge-m3
VEHICLE_AGENT_OLLAMA_EMBEDDING_NUM_GPU=0
VEHICLE_AGENT_EMBEDDING_DIMENSION=1024
VEHICLE_AGENT_EMBEDDING_BATCH_SIZE=16
VEHICLE_AGENT_VECTOR_STORE_PROVIDER=qdrant
VEHICLE_AGENT_QDRANT_URL=http://127.0.0.1:6333
VEHICLE_AGENT_QDRANT_COLLECTION_NAME=vehicle_knowledge_v1
VEHICLE_AGENT_RAG_CANDIDATE_MULTIPLIER=2
VEHICLE_AGENT_RETRIEVAL_MODE=hybrid
VEHICLE_AGENT_EVIDENCE_MIN_DENSE_SCORE=0.35
VEHICLE_AGENT_RERANKER_PROVIDER=pass_through
VEHICLE_AGENT_RERANKER_MODEL=BAAI/bge-reranker-base
VEHICLE_AGENT_RERANKER_BATCH_SIZE=8
VEHICLE_AGENT_SESSION_MEMORY_PROVIDER=redis
VEHICLE_AGENT_REDIS_URL=redis://127.0.0.1:6379/0
VEHICLE_AGENT_SESSION_TTL_SECONDS=1800
VEHICLE_AGENT_SESSION_MAX_TURNS=10
VEHICLE_AGENT_CONTEXT_MAX_CHARACTERS=16000
VEHICLE_AGENT_CONTEXT_MAX_HISTORY_TURNS=6
```

Why these parameters:

- `1024` is fixed by BGE-M3 dense output; it is not a tuning parameter.
- `NUM_GPU=0` is required on this machine's 2 GB GPU because Ollama GPU
  offloading produced NaN embeddings; omit it on a sufficiently capable GPU.
- Batch `16` is a safe local baseline. Tune from measured throughput and memory.
- Candidate multiplier `2` retrieves `2 * Top-K` before reranking.
- `hybrid` combines Qdrant dense results with the curated corpus's BM25 ranking.
  RRF uses rank positions because cosine and BM25 scores have different scales.
- Gate threshold `0.35` is an initial heuristic. Calibrate it on labeled queries,
  balancing false acceptance against unnecessary fallback.
- Rerank batch `8` bounds local CPU work. The model is lazy-loaded and runs in a
  worker thread so synchronous ONNX inference does not block the event loop.
- The current environment uses `pass_through`: hybrid retrieval improved recall at
  low cost, while the Cross-Encoder added substantial CPU latency without improving
  Hit@3. Set the provider to `fastembed` for experiments or offline evaluation.
- Redis keeps at most 10 recent exchanges and refreshes a 30-minute TTL on append.
  Redis failure is non-critical: the request continues without history.
- The context limit is currently measured in serialized characters, not exact model
  tokens, because the configured remote provider does not expose its tokenizer.

## Run The Real RAG Path

```powershell
cd server-v2
docker compose up -d
uv run python -m scripts.ingest_knowledge
uv run python -m scripts.smoke_rag_retrieval
uv run python -m scripts.smoke_rag_retrieval --reranker fastembed
uv run python -m scripts.eval_retrieval
uv run python -m scripts.smoke_vehicle_qa --timeout 60
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

OpenAPI is available at `http://127.0.0.1:8000/docs`; Qdrant dashboard is at
`http://127.0.0.1:6333/dashboard`.

Delete one short-term conversation with:

```http
DELETE /qa/sessions/{session_id}/memory
```

The full smoke uses the configured chat provider. To test the local chat model,
run `uv run python -m scripts.smoke_vehicle_qa --provider ollama --timeout 180`;
on this 16 GB / 2 GB VRAM machine that path may correctly end in timeout fallback.

The tracked corpus contains 28 reviewed summary chunks across MAF, MAP, coolant
temperature, cooling, oxygen sensors, fuel trim, throttle, charging, and OBD/DTC.
Each chunk stores source, topic, PID tags, DTC codes, language, and scope metadata.

The ingestion path is idempotent: `chunk_id` is converted to deterministic UUID5,
so rebuilding the same chunks updates points instead of duplicating them. When the
embedding model or dimension changes, use a versioned collection name and rebuild.

## Failure Strategy

| Failure | Behavior |
|---|---|
| Embedding/Qdrant unavailable | Retrieval failure trace, then rule fallback |
| BM25 unavailable/disabled | Continue with dense retrieval |
| Reranker unavailable | Log provider failure and retain hybrid retrieval order |
| No result or score below gate | `insufficient_retrieval_evidence` |
| Chat timeout/connection/rate limit | Retried when safe, then rule fallback |
| Repeated chat provider failures | Circuit opens; subsequent model calls fail fast into fallback |
| Request deadline exhausted | Cancel pending async work; return rule fallback with `request_deadline` trace |
| Truncated or invalid model JSON | Schema parsing fails, then rule fallback |
| Invalid API request | FastAPI/Pydantic returns 422 before workflow execution |
| Missing/incorrect configured service key | 401 with Bearer challenge |
| Redis unavailable | Continue with empty history; log only sanitized error type |
| Mandatory context exceeds budget | Rule fallback instead of sending a truncated structure |

Fallback is not a hidden second LLM call. The service first prepares a deterministic
rule answer and returns it if an uncertain external component fails. `answer_mode`
describes which branch produced the answer; `agent_trace` records node outcomes.

### Reliability Parameters

| Setting suffix (prefix: `VEHICLE_AGENT_`) | Default | Meaning |
|---|---:|---|
| `REQUEST_DEADLINE_SECONDS` | 60 | Total async service budget, including memory, retrieval, retries and generation |
| `MODEL_CIRCUIT_FAILURE_THRESHOLD` | 5 | Failed requests after retry exhaustion before opening |
| `MODEL_CIRCUIT_RECOVERY_SECONDS` | 30 | Cooldown before allowing one half-open probe |

The breaker wraps the retry adapter and lives in application state, so successive
requests share it. Retryable provider failures count toward the threshold; invalid
requests do not. Successful calls reset the counter. A failed or cancelled recovery
probe reopens the circuit. Late completions from an older circuit epoch cannot close
it. Breakers are per process and currently protect only chat generation.

The deadline starts when the route calls the QA service, after request validation
and dependency assembly. It is cooperative asyncio cancellation, not a hard kill:
blocking synchronous work, already-running inference threads, remote server work,
and completed Redis writes cannot be rolled back. Deadline fallback does not append
a new history turn. The deadline trace is a new fallback trace, not a persisted
snapshot of the interrupted workflow.

## Verification

```powershell
uv run pytest
uv run ruff check .
uv run mypy app scripts
```

Tests cover schemas, provider error mapping, retry behavior, workflow branches,
embedding validation, vector CRUD, ingestion, retrieval, evidence gating, fallback,
rerank fallback, retrieval metrics, and the API closed loop. Real smoke scripts
additionally verify Ollama, Qdrant, and the ONNX Cross-Encoder.

## Evaluation Plan

Create a reviewed query set with relevant chunk IDs and expected answer facts.
Report retrieval and answer metrics separately:

- Hit@K: whether Top-K contains at least one relevant chunk.
- Recall@K: proportion of all labeled relevant chunks recovered.
- MRR: rank of the first relevant chunk.
- Precision@K: irrelevant-content pressure in the context window.
- Context recall/faithfulness: fact coverage and whether claims are evidence-backed.
- Operational: p50/p95 latency, fallback rate, provider error rate, and token cost.

Tune chunking, Top-K, reranker, and gate threshold against the fixed evaluation set.
`scripts/eval_retrieval.py` compares dense, hybrid, and hybrid-plus-reranker paths on
the reviewed cases in `eval/retrieval_cases.json`. The current 27-case set covers
nine topics and hard negatives, but is still too small for production claims.

Initial local result:

| Pipeline | Hit@3 | Recall@3 | MRR | Mean latency |
|---|---:|---:|---:|---:|
| BGE-M3 dense | 0.889 | 0.889 | 0.802 | 482 ms |
| Dense + BM25 + RRF | 0.926 | 0.926 | 0.870 | 498 ms |
| Hybrid + BGE reranker | 0.926 | 0.926 | 0.883 | 2134 ms |

Hybrid retrieval recovered two exact-term MAF cases with little extra latency. The
Cross-Encoder improved only first-result ordering and cost roughly four times the
latency, so hybrid plus pass-through is the active default.

## Why Not LangGraph Yet

The current graph is a short acyclic workflow with explicit state, node contracts,
conditional fallback, and trace output. Adding LangGraph now would mostly replace
visible Python routing with framework APIs. Migrate when the product needs durable
checkpoints, pause/resume, human approval, parallel tool branches, bounded reasoning
loops, or multi-agent handoffs. The typed `VehicleAgentState` and node boundaries
already provide a clean migration path.

## Current Boundaries

- Hybrid retrieval is implemented with a compact in-memory BM25 index. A larger or
  frequently updated corpus should move lexical indexing to OpenSearch/Qdrant sparse.
- FastEmbed reranking is implemented and locally cached, but disabled by default
  based on the current evaluation result.
- Qdrant payload stores chunk metadata; request-time metadata filters are a planned
  extension once vehicle/model labels are sufficiently reliable.
- Session keys are hashed, but hashing is not authorization. Authenticated user and
  vehicle ownership, long-term memory and checkpoint recovery remain unimplemented.

See [task progress](docs/task_progress.md) for the completed milestones and next
stage, and [reliability learning card](docs/learning_cards/reliability_controls.md)
for the deadline/retry/circuit-breaker distinction and debugging examples.

Learning cards are under `docs/learning_cards/`. Start with
`minimal_rag_closed_loop.md`, `qdrant_vector_store_operations.md`, and
`local_rag_environment.md`. Current production gaps and their priority are tracked in
`docs/remaining_engineering_gaps.md`.
