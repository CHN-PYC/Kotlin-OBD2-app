"""Explicit local embedding smoke test; never downloads models or writes vectors."""

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx2

from app.providers.embedding import EmbeddingRequest
from app.providers.errors import ModelProviderError
from app.providers.ollama_embedding import OllamaEmbeddingModel
from app.schemas.knowledge import KnowledgeChunk


async def check(args: argparse.Namespace) -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "data/processed/hella_air_mass_sensor.chunks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    chunks = [KnowledgeChunk.model_validate(item) for item in payload["chunks"]]
    request = EmbeddingRequest(texts=[chunk.text for chunk in chunks])
    async with httpx2.AsyncClient() as client:
        model = OllamaEmbeddingModel(
            base_url=args.base_url,
            model_name=args.model,
            expected_dimension=args.dimension,
            timeout_seconds=args.timeout,
            num_gpu=args.num_gpu,
            client=client,
        )
        started = time.perf_counter()
        result = await model.embed(request)
    print(f"Model: {result.model}; elapsed: {time.perf_counter() - started:.2f}s")
    # embed has already validated counts; strict zip additionally prevents silent mismatch.
    for chunk, vector in zip(chunks, result.vectors, strict=True):
        print(f"{chunk.chunk_id}: dimension={len(vector)}")
    print("Validated embeddings in memory only; no vector index was created.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="bge-m3")
    parser.add_argument("--dimension", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--num-gpu", type=int, default=0)
    args = parser.parse_args()
    try:
        asyncio.run(check(args))
    except ModelProviderError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
