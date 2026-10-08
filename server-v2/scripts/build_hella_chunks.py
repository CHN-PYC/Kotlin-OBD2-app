"""Export inspectable candidate chunks, without network calls or embeddings."""

import json
from pathlib import Path

from app.services.knowledge.chunk_builder import build_section_chunks
from app.services.knowledge.html_extractor import ExtractedArticle


def export_chunks(input_path: Path, output_path: Path) -> int:
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Output must not overwrite the extracted article")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    article = ExtractedArticle.model_validate(payload)
    source = payload["source"]
    chunks = build_section_chunks(article, doc_id=source["doc_id"], source_url=source["source_url"])
    if not chunks:
        raise ValueError("No candidate chunks to export")
    # Keep the original provenance outside the chunks for this single-document artifact.
    result = {
        "source": source,
        "extractor_version": payload["extractor_version"],
        "chunker_version": "section-v1",
        "status": "candidate_not_token_checked",
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8")
    return len(chunks)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    input_path = root / "data/processed/hella_air_mass_sensor.json"
    output_path = root / "data/processed/hella_air_mass_sensor.chunks.json"
    count = export_chunks(input_path, output_path)
    print(f"Exported {count} candidate chunks (not token checked)")
    print(output_path)


if __name__ == "__main__":
    main()
