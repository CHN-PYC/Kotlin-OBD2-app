import json
from pathlib import Path

import httpx2
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.schemas.knowledge import KnowledgeChunk
from app.schemas.vector_store import VectorRecord
from app.services.retrieval.memory_vector_store import MemoryVectorStore

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def request_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def knowledge_record(vector: list[float]) -> VectorRecord:
    return VectorRecord(
        vector=vector,
        chunk=KnowledgeChunk(
            chunk_id="cooling-check",
            doc_id="vehicle-guide",
            title="Cooling system guide",
            section_title="High coolant temperature",
            source_url="https://example.com/cooling",
            text="When coolant temperature is high, inspect the cooling fan and coolant level.",
        ),
    )


def test_api_runs_embedding_retrieval_gate_prompt_and_generation() -> None:
    captured_chat_payloads: list[dict] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/api/embed":
            return httpx2.Response(200, json={"model": "bge-m3", "embeddings": [[1.0, 0.0]]})
        if request.url.path == "/api/chat":
            captured_chat_payloads.append(json.loads(request.content))
            return httpx2.Response(
                200,
                json={
                    "model": "qwen3:4b",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "answer": "Inspect the cooling fan and coolant level.",
                                "findings": ["Coolant temperature is high."],
                                "recommendations": ["Inspect the cooling fan."],
                            }
                        ),
                    },
                    "done": True,
                    "done_reason": "stop",
                },
            )
        raise AssertionError(f"unexpected outbound path: {request.url.path}")

    async def vector_store_factory(settings: Settings) -> MemoryVectorStore:
        store = MemoryVectorStore(dimension=2)
        await store.upsert([knowledge_record([1.0, 0.0])])
        return store

    outbound = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    app = create_app(
        settings=Settings(
            _env_file=None,
            ollama_chat_model="qwen3:4b",
            ollama_embedding_model="bge-m3",
            embedding_dimension=2,
            evidence_min_dense_score=0.35,
        ),
        client_factory=lambda: outbound,
        vector_store_factory=vector_store_factory,
    )

    with TestClient(app) as client:
        response = client.post("/qa/vehicle", json=request_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["answer_mode"] == "llm_rag"
    assert [source["chunk_id"] for source in body["sources"]] == ["cooling-check"]
    assert [step["step"] for step in body["agent_trace"]] == [
        "prepare_baseline",
        "query_rewrite",
        "retrieval_tool",
        "evidence_gate",
        "prompt_build",
        "model_generation",
        "model_output_parse",
        "build_response",
    ]
    prompt = json.loads(captured_chat_payloads[0]["messages"][1]["content"])
    assert prompt["retrievedEvidence"][0]["chunk_id"] == "cooling-check"


def test_evidence_gate_returns_rule_fallback_without_calling_chat_model() -> None:
    chat_calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal chat_calls
        if request.url.path == "/api/embed":
            return httpx2.Response(200, json={"model": "bge-m3", "embeddings": [[1.0, 0.0]]})
        chat_calls += 1
        return httpx2.Response(500)

    async def vector_store_factory(settings: Settings) -> MemoryVectorStore:
        store = MemoryVectorStore(dimension=2)
        await store.upsert([knowledge_record([0.0, 1.0])])
        return store

    outbound = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    app = create_app(
        settings=Settings(
            _env_file=None,
            ollama_chat_model="qwen3:4b",
            ollama_embedding_model="bge-m3",
            embedding_dimension=2,
            evidence_min_dense_score=0.35,
        ),
        client_factory=lambda: outbound,
        vector_store_factory=vector_store_factory,
    )

    with TestClient(app) as client:
        response = client.post("/qa/vehicle", json=request_payload())

    assert response.status_code == 200
    assert response.json()["answer_mode"] == "insufficient_retrieval_evidence"
    assert [step["step"] for step in response.json()["agent_trace"]][-2:] == [
        "evidence_gate",
        "rule_fallback",
    ]
    assert chat_calls == 0


def test_embedding_timeout_returns_rule_fallback_without_calling_chat_model() -> None:
    chat_calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal chat_calls
        if request.url.path == "/api/embed":
            raise httpx2.ReadTimeout("slow embedding", request=request)
        chat_calls += 1
        return httpx2.Response(500)

    async def vector_store_factory(settings: Settings) -> MemoryVectorStore:
        return MemoryVectorStore(dimension=2)

    outbound = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    app = create_app(
        settings=Settings(
            _env_file=None,
            ollama_chat_model="qwen3:4b",
            ollama_embedding_model="bge-m3",
            embedding_dimension=2,
        ),
        client_factory=lambda: outbound,
        vector_store_factory=vector_store_factory,
    )

    with TestClient(app) as client:
        response = client.post("/qa/vehicle", json=request_payload())

    assert response.status_code == 200
    assert response.json()["answer_mode"] == "rule_fallback"
    assert [step["step"] for step in response.json()["agent_trace"]][-2:] == [
        "retrieval_tool",
        "rule_fallback",
    ]
    assert response.json()["agent_trace"][-2]["status"] == "failed"
    assert chat_calls == 0
