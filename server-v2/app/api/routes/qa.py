import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response, status

from app.agent.nodes import (
    BuildPromptNode,
    BuildResponseNode,
    EvidenceGateNode,
    GenerateModelNode,
    ParseModelOutputNode,
    PrepareBaselineNode,
    RetrieveEvidenceNode,
    RewriteQueryNode,
    RuleFallbackNode,
)
from app.agent.workflow import WorkFlow
from app.contracts.vector_store import VectorStore
from app.providers.chat import ChatModel
from app.providers.embedding import EmbeddingModel
from app.schemas.qa import VehicleQARequest, VehicleQAResponse
from app.services.generation.answer_parser import VehicleAnswerParser
from app.services.generation.context_manager import ContextWindowManager
from app.services.generation.deadline import DeadlineQAService
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.generation.qa_service import RuleFallbackQAService, VehicleQAService
from app.services.generation.workflow_qa_service import WorkflowQAService
from app.services.memory.errors import SessionMemoryError
from app.services.retrieval.query_retrieval import QueryRetrievalService
from app.services.retrieval.query_rewrite import DeterministicQueryRewriter
from app.services.retrieval.reranking import Reranker
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline
from app.tools.factory import create_vehicle_tool_registry

router = APIRouter(prefix="/qa", tags=["vehicle-qa"])


def verify_service_auth(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    configured = request.app.state.settings.api_key
    if configured is None:
        # LEARNING: an empty API key keeps local development convenient. Production
        # should always configure one; upstream LLM credentials are unrelated.
        return
    expected = f"Bearer {configured.get_secret_value()}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        # compare_digest avoids content-dependent comparison timing for secret values.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_vehicle_qa_service(request: Request) -> VehicleQAService:
    # LEARNING: 这是 FastAPI Request；业务 JSON 对应下面的 VehicleQARequest。
    model: ChatModel | None = request.app.state.chat_model
    if model is None:
        return RuleFallbackQAService()
    embedding_model: EmbeddingModel | None = request.app.state.embedding_model
    settings = request.app.state.settings
    retrieval_node: RetrieveEvidenceNode | None = None
    evidence_gate_node: EvidenceGateNode | None = None
    if embedding_model is not None:
        vector_store: VectorStore = request.app.state.vector_store
        reranker: Reranker = request.app.state.reranker
        retrieval_service = QueryRetrievalService(
            embedding_model=embedding_model,
            pipeline=RetrievalPipeline(
                vector_store,
                reranker,
                request.app.state.lexical_retriever,
            ),
            expected_dimension=settings.embedding_dimension,
            candidate_multiplier=settings.rag_candidate_multiplier,
        )
        retrieval_node = RetrieveEvidenceNode(
            tool_registry=create_vehicle_tool_registry(retrieval_service)
        )
        evidence_gate_node = EvidenceGateNode(
            min_dense_score=settings.evidence_min_dense_score,
        )
    # LEARNING: 依赖函数负责组装；Workflow 每次 run 创建独立的请求状态。
    return WorkflowQAService(
        workflow=WorkFlow(
            prepare_node=PrepareBaselineNode(fallback=RuleFallbackQAService()),
            prompt_node=BuildPromptNode(
                prompt_builder=VehicleQAPromptBuilder(
                    options=request.app.state.chat_options,
                    context_manager=ContextWindowManager(
                        max_characters=settings.context_max_characters,
                        max_history_turns=settings.context_max_history_turns,
                    ),
                )
            ),
            generate_node=GenerateModelNode(model=model),
            parse_node=ParseModelOutputNode(answer_parser=VehicleAnswerParser()),
            fallback_node=RuleFallbackNode(),
            response_node=BuildResponseNode(),
            retrieval_node=retrieval_node,
            evidence_gate_node=evidence_gate_node,
            rewrite_node=RewriteQueryNode(rewriter=DeterministicQueryRewriter()),
        ),
        memory_store=request.app.state.session_memory_store,
    )


@router.post("/vehicle", response_model=VehicleQAResponse)
async def answer_vehicle_question(
    request: VehicleQARequest,
    http_request: Request,
    _: Annotated[None, Depends(verify_service_auth)],
    service: Annotated[VehicleQAService, Depends(get_vehicle_qa_service)],
) -> VehicleQAResponse:
    # LEARNING: 路由只做协议边界和调用，不在这里拼 Prompt 或直接访问 Ollama。
    return await DeadlineQAService(
        service,
        seconds=http_request.app.state.settings.request_deadline_seconds,
    ).answer(request)


@router.delete(
    "/sessions/{session_id}/memory",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def clear_session_memory(
    request: Request,
    _: Annotated[None, Depends(verify_service_auth)],
    session_id: Annotated[str, Path(min_length=1, max_length=128)],
) -> Response:
    try:
        await request.app.state.session_memory_store.clear(session_id)
    except SessionMemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session memory is temporarily unavailable",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
