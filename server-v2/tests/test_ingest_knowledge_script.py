import json
from pathlib import Path

import pytest

from scripts.ingest_knowledge import load_chunks


def write_chunks(path: Path, chunk_ids: list[str]) -> None:
    chunks = [
        {
            "chunk_id": chunk_id,
            "doc_id": "doc",
            "title": "Guide",
            "section_title": "Checks",
            "source_url": "https://example.com",
            "text": f"Evidence {chunk_id}",
            "topic": "test",
        }
        for chunk_id in chunk_ids
    ]
    path.write_text(json.dumps({"chunks": chunks}), encoding="utf-8")


def test_load_chunks_combines_multiple_files(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_chunks(first, ["a"])
    write_chunks(second, ["b"])

    chunks = load_chunks([first, second])

    assert [chunk.chunk_id for chunk in chunks] == ["a", "b"]
    assert chunks[0].topic == "test"


def test_load_chunks_rejects_ids_duplicated_across_files(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_chunks(first, ["same"])
    write_chunks(second, ["same"])

    with pytest.raises(ValueError, match="duplicate"):
        load_chunks([first, second])
