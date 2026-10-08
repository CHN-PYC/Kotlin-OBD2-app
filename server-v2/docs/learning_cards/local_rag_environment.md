# Learning Card: Local RAG Environment

## Purpose

Provide a reproducible local runtime for the real RAG path: Ollama serves
`bge-m3`, Qdrant persists vectors and payload metadata, and FastAPI owns the
application resources.

## Input And Output

- Input: validated `KnowledgeChunk` JSON and a user query.
- Output: 1024-dimensional vectors, persisted Qdrant points, and ranked sources.

## Data Flow

```text
chunk JSON -> Ollama bge-m3 -> VectorRecord -> Qdrant upsert
query      -> Ollama bge-m3 -> Qdrant cosine Top-K -> reranker -> evidence gate
```

## Selection Rationale

- `bge-m3`: multilingual dense embeddings, appropriate for Chinese vehicle terms
  mixed with English PID/DTC names; its dense output is 1024 dimensions.
- Qdrant: persists vectors and JSON payloads, supports update/delete/filtering,
  and has a service boundary that is closer to production than process memory.
- Docker Compose: pins the Qdrant version and keeps data in a named volume.
- Batch size 16: conservative local default that limits memory and request size;
  benchmark throughput before increasing it.
- `num_gpu=0`: local hardware compatibility setting after a 2 GB GPU produced
  NaN embeddings. This is not an embedding-quality parameter.

## Important Invariants

- Query and document embeddings must use the same model and dimension.
- Collection distance is cosine because the evidence threshold uses cosine scores.
- A stable UUID5 is derived from `chunk_id`, so repeated ingestion is idempotent.
- Use a new collection name when changing the embedding model or dimension.

## Failure Cases And Debugging

- Ollama connection failure: check `ollama list` and port `11434`.
- Qdrant connection failure: run `docker compose ps` and check `/healthz`.
- Dimension mismatch: compare the model output, `EMBEDDING_DIMENSION`, and
  collection vector size. Do not pad or truncate vectors.
- Empty retrieval: verify ingestion count, query language, threshold, and Top-K.

## Verification

```powershell
ollama list
docker compose up -d
uv run python -m scripts.ingest_knowledge
uv run python -m scripts.smoke_rag_retrieval
uv run pytest
```

## Evaluation And Replacement

Measure Recall@K, MRR, Precision@K, evidence-gate fallback rate, and p95 latency.
Qdrant can be replaced through `VectorStore`; the local memory implementation is
the deterministic test double. A cross-encoder can replace the pass-through
reranker after an evaluated reranking model is selected.
