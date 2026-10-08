import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.retrieval import RetrievedSource


def _valid_source_data() -> dict:
    return {
        "chunk_id": "chunk-001",
        "doc_id": "doc-001",
        "title": "Cooling system guide",
        "source_url": "",
        "score": 0.82,
        "text": "Check coolant level and radiator fan operation.",
        "topic": "cooling_system",
        "pid_tags": ["ECT"],
        "page_start": 1,
        "page_end": 2,
        "section_title": "Cooling system diagnosis",
    }


def test_response_fixture_contains_valid_source() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_response.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    source = RetrievedSource.model_validate(payload["sources"][0])

    assert source.score == 0.82
    assert source.pid_tags == ["ECT"]


def test_source_rejects_string_score() -> None:
    data = _valid_source_data()
    data["score"] = "0.82"

    with pytest.raises(ValidationError):
        RetrievedSource.model_validate(data)


@pytest.mark.parametrize("field", ["chunk_id", "doc_id", "title", "text"])
def test_source_rejects_blank_required_text(field: str) -> None:
    data = _valid_source_data()
    data[field] = "   "

    with pytest.raises(ValidationError):
        RetrievedSource.model_validate(data)


def test_source_rejects_page_number_below_one() -> None:
    data = _valid_source_data()
    data["page_start"] = 0

    with pytest.raises(ValidationError):
        RetrievedSource.model_validate(data)


def test_source_rejects_pid_tags_string_instead_of_list() -> None:
    data = _valid_source_data()
    data["pid_tags"] = "ECT"

    with pytest.raises(ValidationError):
        RetrievedSource.model_validate(data)


def test_source_supplies_optional_metadata_defaults() -> None:
    source = RetrievedSource(
        chunk_id="chunk-001",
        doc_id="doc-001",
        title="Cooling system guide",
        score=0.5,
        text="Check the cooling system.",
    )

    assert source.source_url == ""
    assert source.topic is None
    assert source.pid_tags == []
    assert source.page_start is None
    assert source.page_end is None
    assert source.section_title is None
