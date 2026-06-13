# Vehicle RAG Server

FastAPI backend skeleton for vehicle diagnostic RAG.

## What this scaffold includes

- `/kb/documents` for ingesting knowledge documents
- `/kb/rebuild` for rebuilding the vector index
- `/kb/status` for index/document stats
- `/qa/vehicle` for vehicle-context Q&A
- local TF-IDF embedding + persisted vectorizer for usable retrieval now
- JSON-backed vector index with FAISS-compatible service boundaries
- real OpenAI-compatible LLM call boundary via `httpx`

## Run locally

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload
```

## Seed sample docs

```bash
cd server
PYTHONPATH=. python scripts/seed_kb.py
```

## Configure LLM

Set these before starting the server:

```bash
export LLM_BASE_URL=https://your-endpoint/v1/chat/completions
export LLM_API_KEY=sk-...
export LLM_MODEL=gpt-4o-mini
```

## Next replacements

1. Replace `app/services/embedding_service.py` TF-IDF baseline with dense embeddings if needed.
2. Replace `app/services/vector_store_service.py` internals with FAISS when the package/runtime is available.
3. Replace TF-IDF with dense embeddings when you need stronger semantic recall.
4. Replace the JSON-backed vector index with FAISS when the runtime provides it.
