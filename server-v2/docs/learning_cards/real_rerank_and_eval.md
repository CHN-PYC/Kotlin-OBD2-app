# Learning Card: Real Rerank And Retrieval Evaluation

## Purpose

Improve ordering after broad dense recall, while measuring whether the added model
actually helps. Rerank cannot recover a relevant chunk that was absent from the
candidate set.

## Input And Output

- Input: one query and `candidate_k` chunks from Qdrant.
- Output: all candidate IDs with Cross-Encoder logits, sorted to `final_k`.
- Evaluation input: reviewed queries plus their relevant chunk IDs.
- Evaluation output: Hit@K, Recall@K, Precision@K, MRR, and latency.

## Algorithm

```text
BGE-M3 query vector -> Qdrant candidate Top-K
query + each candidate text -> BGE reranker logit
sort logits descending -> final Top-K
```

`BAAI/bge-reranker-base` uses joint query-document attention, unlike bi-encoder
retrieval where query and chunks are encoded independently. This costs more per
candidate but can model detailed term relationships.

## Selection Rationale

- Chinese and English support matches Chinese questions with English repair sources.
- FastEmbed uses ONNX Runtime, avoiding a large PyTorch runtime on this laptop.
- The 1.04 GB base model fits local disk and memory better than the 2.29 GB
  `bge-reranker-v2-m3` checkpoint.
- Batch size 8 is a conservative CPU default and must be benchmarked.

## Failure And Fallback

The model loads lazily. Provider failure is sanitized and logged without query or
document content. `ResilientReranker` then copies dense scores, preserving useful
retrieval instead of failing the complete diagnosis.

The Evidence Gate deliberately uses dense cosine score. Cross-Encoder outputs are
model-specific logits and are not calibrated probabilities, so applying the dense
`0.35` threshold to them would be invalid.

## Debugging

- Trace says `fastembed:...`: real rerank ran.
- Trace says `pass_through`: rerank is disabled or fell back.
- First request is slow: inspect model download/cache and cold-start time.
- Wrong ordering: inspect candidate recall first; rerank cannot repair missed recall.

## Verification

```powershell
uv run python -m scripts.smoke_rag_retrieval
uv run python -m scripts.eval_retrieval
uv run pytest
```

## Evaluation Limits

The current 27 cases cover nine diagnostic topics, exact codes, colloquial questions,
and confusing neighboring topics. They validate the comparison pipeline but remain
too small and manually authored for production quality claims.

On the expanded corpus, dense retrieval measured Hit@3 `0.889` and MRR `0.802`.
Hybrid retrieval raised these to `0.926` and `0.870` at about 498 ms/query. Adding
the Cross-Encoder kept Hit@3 at `0.926`, raised MRR only to `0.883`, and increased
latency to about 2134 ms/query. Therefore hybrid retrieval is active while the model
reranker remains an evaluated optional component.

## Replacement

The provider can be disabled with `RERANKER_PROVIDER=pass_through`, replaced by a
remote rerank API, or upgraded to another multilingual Cross-Encoder without changing
the retrieval pipeline contract.
