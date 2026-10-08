# Learning Card: Hybrid Retrieval

## Purpose

Dense Embedding handles paraphrases and semantic similarity. BM25 adds exact lexical
signals such as `P0171`, `STFT`, PID names, voltages, and component terminology. RRF
combines both rankings without pretending their raw scores share a unit.

## Data Flow

```text
query -> BGE-M3 -> Qdrant cosine candidates ----+
query -> Chinese/code tokenizer -> BM25 --------+-> RRF -> optional rerank -> Top-K
```

The BM25 corpus is loaded from tracked `knowledge/*.chunks.json` files at startup.
Qdrant remains the persistent vector store. BM25 is currently in process because 28
chunks are tiny; this is not a suitable architecture for millions of documents.

## Core Algorithms

- BM25 uses `k1=1.5` for term-frequency saturation and `b=0.75` for document-length
  normalization.
- The tokenizer keeps ASCII codes as complete lowercase terms and creates Chinese
  characters plus bigrams. This is deliberately dependency-free and easy to inspect.
- RRF adds `1 / (60 + rank)` for each retrieval list. It uses rank, not raw score.
- `source.score` remains dense cosine similarity for Evidence Gate. An internal
  `rank_score` carries RRF ordering so score semantics are not accidentally mixed.

## Failure Cases And Debugging

- Exact code missing: inspect tokenizer output and whether the chunk contains the code.
- Hybrid order equals dense: verify the pass-through reranker uses `rank_score`.
- Lexical-only result: its dense score is zero, so it cannot alone bypass the current
  Evidence Gate. This conservative behavior avoids treating term overlap as proof.
- Corpus update: re-run ingestion for Qdrant and restart the API to rebuild in-memory
  BM25 from the same tracked chunk files.

## Evaluation

On 27 reviewed cases, Hit@3 changed from `0.889` to `0.926`, MRR from `0.802` to
`0.870`, and mean latency from about `482 ms` to `498 ms`. These local figures explain
the default choice but do not establish production quality.

## Replacement

For a large or frequently updated corpus, move lexical indexing to OpenSearch,
Elasticsearch, or a vector database sparse-vector feature. Keep the retrieval and
fusion contracts so the Agent workflow does not need to change.
