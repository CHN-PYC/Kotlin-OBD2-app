import asyncio
from pathlib import Path

import pytest

from app.schemas.qa import VehicleQARequest
from app.schemas.reranking import RerankedSource
from app.schemas.retrieval import RetrievedSource
from app.tools.factory import create_vehicle_tool_registry
from app.tools.registry import ToolInputValidationError
from app.tools.vehicle import (
    DtcInterpretOutput,
    KnowledgeSearchOutput,
    PidLookupOutput,
    SessionSignalOutput,
)

FIXTURE = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


class FakeRetrievalService:
    async def retrieve(self, query_text: str, *, final_k: int) -> list[RerankedSource]:
        source = RetrievedSource(
            chunk_id="cooling",
            doc_id="guide",
            title="Cooling guide",
            score=0.8,
            text="Inspect coolant level and fan operation.",
        )
        return [
            RerankedSource(
                source=source,
                rerank_score=0.8,
                rerank_provider="pass_through",
            )
        ][:final_k]


def registry():
    return create_vehicle_tool_registry(FakeRetrievalService())  # type: ignore[arg-type]


def test_registers_expected_vehicle_tool_whitelist() -> None:
    assert registry().names() == [
        "analyze_session_signals",
        "interpret_dtc",
        "lookup_pid_definition",
        "search_vehicle_knowledge",
    ]


def test_search_and_pid_tools_return_typed_outputs() -> None:
    tools = registry()

    search = KnowledgeSearchOutput.model_validate(
        asyncio.run(tools.invoke("search_vehicle_knowledge", {"query": "水温高", "top_k": 1}))
    )
    pids = PidLookupOutput.model_validate(
        asyncio.run(tools.invoke("lookup_pid_definition", {"pids": ["ect", "unknown"]}))
    )

    assert search.sources[0].source.chunk_id == "cooling"
    assert pids.definitions[0].pid == "ECT"
    assert pids.unknown_pids == ["UNKNOWN"]


def test_dtc_tool_validates_format_and_avoids_part_replacement_claim() -> None:
    tools = registry()
    result = DtcInterpretOutput.model_validate(
        asyncio.run(tools.invoke("interpret_dtc", {"code": "P0171"}))
    )

    assert result.family == "air_fuel_metering"
    assert "not proof" in result.diagnostic_note
    with pytest.raises(ToolInputValidationError):
        asyncio.run(tools.invoke("interpret_dtc", {"code": "171"}))


def test_session_tool_flags_high_coolant_without_claiming_root_cause() -> None:
    request = VehicleQARequest.model_validate_json(FIXTURE.read_text(encoding="utf-8"))

    result = SessionSignalOutput.model_validate(
        asyncio.run(
            registry().invoke(
                "analyze_session_signals",
                {"summary": request.vehicle_context.session_summary.model_dump()},
            )
        )
    )

    assert [item.code for item in result.observations] == ["COOLANT_HIGH"]
    assert result.limitations
