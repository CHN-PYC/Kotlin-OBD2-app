"""Embed validated chunk JSON and upsert it into the configured VectorStore."""

import argparse
import asyncio
from pathlib import Path

import httpx2

from app.core.config import Settings
from app.providers.factory import create_embedding_model, create_vector_store
from app.services.knowledge.corpus_loader import load_chunks
from app.services.knowledge.ingestion import KnowledgeIngestionService


def parse_paths(root: Path) -> list[Path]:
    parser = argparse.ArgumentParser(description="Embed and upsert curated knowledge chunks")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="chunk JSON files; defaults to knowledge/*.chunks.json",
    )
    args = parser.parse_args()
    paths = args.paths or sorted((root / "knowledge").glob("*.chunks.json"))
    if not paths:
        raise FileNotFoundError("no knowledge chunk files found")
    return [path if path.is_absolute() else root / path for path in paths]


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    chunks = load_chunks(parse_paths(root))
    settings = Settings()

    async with httpx2.AsyncClient() as client:
        vector_store = await create_vector_store(settings)
        try:
            service = KnowledgeIngestionService(
                embedding_model=create_embedding_model(settings, client=client),
                vector_store=vector_store,
                expected_dimension=settings.embedding_dimension,
                batch_size=settings.embedding_batch_size,
            )
            report = await service.ingest(chunks)
            print(report.model_dump_json())
        finally:
            await vector_store.aclose()


if __name__ == "__main__":
    asyncio.run(main())
