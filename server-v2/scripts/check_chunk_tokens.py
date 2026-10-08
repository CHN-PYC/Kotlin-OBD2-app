"""Inspect candidate chunks using the pinned BGE-M3 tokenizer; no embedding calls."""

import hashlib
import json
from pathlib import Path

from app.schemas.knowledge import KnowledgeChunk
from app.services.knowledge.token_budget import validate_token_budget
from app.services.knowledge.token_counter import LocalTokenCounter


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    metadata = json.loads((root / "data/sources/bge_m3_tokenizer.json").read_text(encoding="utf-8"))
    tokenizer_path = root / metadata["local_path"]
    if hashlib.sha256(tokenizer_path.read_bytes()).hexdigest() != metadata["sha256"]:
        raise ValueError("Tokenizer hash mismatch; review the local artifact")
    counter = LocalTokenCounter(tokenizer_path)
    source = root / "data/processed/hella_air_mass_sensor.chunks.json"
    raw = source.read_bytes()
    payload = json.loads(raw)
    chunks = [KnowledgeChunk.model_validate(value) for value in payload["chunks"]]
    if not chunks:
        raise ValueError("No chunks to check")
    target_budget = 512
    rows = []
    for chunk in chunks:
        try:
            count = validate_token_budget(
                chunk.text, count_tokens=counter.count_tokens, max_tokens=target_budget
            )
            within_budget = True
        except ValueError:
            # Report overflow without truncating or modifying the source chunks.
            count = counter.count_tokens(chunk.text)
            within_budget = False
        rows.append(
            {
                "chunk_id": chunk.chunk_id,
                "token_count": count,
                "within_target_budget": within_budget,
                "within_model_limit": count <= metadata["model_max_length"],
            }
        )
        print(f"{chunk.chunk_id}: {count} tokens; within {target_budget}: {within_budget}")
    report = {
        "tokenizer": metadata,
        "target_budget": target_budget,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "chunks": rows,
    }
    output = root / "data/processed/hella_air_mass_sensor.token_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
