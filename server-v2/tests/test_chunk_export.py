import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.knowledge import KnowledgeChunk
from scripts.build_hella_chunks import export_chunks


def payload() -> dict:
    return {
        "source": {"doc_id": "doc", "source_url": "https://example.com", "sha256": "fixture"},
        "extractor_version": "fixture-v1",
        "title": "Sensor",
        "safety_notes": ["Qualified personnel only."],
        "blocks": [
            {
                "heading_path": ["Sensor", "Checks"],
                "kind": "paragraph",
                "text": "Inspect connections.",
            }
        ],
    }


def test_exports_valid_chunks_and_preserves_provenance(tmp_path: Path) -> None:
    input_path = tmp_path / "article.json"
    output_path = tmp_path / "output/chunks.json"
    original = json.dumps(payload())
    input_path.write_text(original, encoding="utf-8")
    assert export_chunks(input_path, output_path) == 1
    result = json.loads(output_path.read_text(encoding="utf-8"))
    chunk = KnowledgeChunk.model_validate(result["chunks"][0])
    assert chunk.chunk_id == "doc:section:1"
    assert "Safety:" in chunk.text
    assert result["source"] == payload()["source"]
    assert result["status"] == "candidate_not_token_checked"
    assert input_path.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("invalid", ["{", json.dumps({}), json.dumps(payload() | {"blocks": []})])
def test_invalid_input_does_not_overwrite_output(tmp_path: Path, invalid: str) -> None:
    input_path = tmp_path / "article.json"
    output_path = tmp_path / "chunks.json"
    input_path.write_text(invalid, encoding="utf-8")
    output_path.write_text("previous result", encoding="utf-8")
    with pytest.raises((ValueError, ValidationError)):
        export_chunks(input_path, output_path)
    assert output_path.read_text(encoding="utf-8") == "previous result"


def test_rejects_identical_input_output_paths(tmp_path: Path) -> None:
    path = tmp_path / "article.json"
    original = json.dumps(payload())
    path.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="overwrite"):
        export_chunks(path, path)
    assert path.read_text(encoding="utf-8") == original
