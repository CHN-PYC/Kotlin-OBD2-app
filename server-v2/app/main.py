from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx2
from fastapi import FastAPI
from pydantic import BaseModel

from app.api.routes.qa import router as qa_router
from app.contracts.vector_store import VectorStore
from app.core.config import RetrievalMode, Settings, get_settings
from app.providers.chat import ChatOptions
from app.providers.errors import ModelNotConfiguredError
from app.providers.factory import (
    create_chat_model,
    create_embedding_model,
    create_reranker,
    create_vector_store,
)
from app.services.knowledge.corpus_loader import load_curated_corpus
from app.services.memory.factory import create_session_memory_store
from app.services.retrieval.bm25 import BM25Retriever


class HealthResponse(BaseModel):
    status: str


HttpClientFactory = Callable[[], httpx2.AsyncClient]
VectorStoreFactory = Callable[[Settings], Awaitable[VectorStore]]


def create_app(
    *,
    settings: Settings | None = None,
    client_factory: HttpClientFactory = httpx2.AsyncClient,
    vector_store_factory: VectorStoreFactory = create_vector_store,
) -> FastAPI:
    resolved_settings = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        # LEARNING: yield 必须位于 async with 内，否则 client 会在应用运行前关闭。
        async with client_factory() as client:
            application.state.http_client = client
            vector_store = await vector_store_factory(resolved_settings)
            application.state.vector_store = vector_store
            application.state.vector_store_provider_status = "ready"
            application.state.settings = resolved_settings
            session_memory_store = create_session_memory_store(resolved_settings)
            application.state.session_memory_store = session_memory_store
            application.state.lexical_retriever = (
                BM25Retriever(
                    load_curated_corpus(Path(__file__).resolve().parents[1])
                )
                if resolved_settings.retrieval_mode is RetrievalMode.HYBRID
                else None
            )
            try:
                application.state.chat_options = ChatOptions(
                    max_output_tokens=resolved_settings.model_max_output_tokens,
                )
                # The local model is lazy-loaded on first retrieval, so API startup
                # stays fast and an unavailable optional reranker can use dense order.
                application.state.reranker = create_reranker(resolved_settings)
                try:
                    application.state.chat_model = create_chat_model(
                        resolved_settings,
                        client=client,
                    )
                    application.state.model_provider_status = "ready"
                except ModelNotConfiguredError:
                    application.state.chat_model = None
                    application.state.model_provider_status = "not_configured"

                if resolved_settings.ollama_embedding_model is None:
                    application.state.embedding_model = None
                    application.state.embedding_provider_status = "not_configured"
                else:
                    application.state.embedding_model = create_embedding_model(
                        resolved_settings,
                        client=client,
                    )
                    application.state.embedding_provider_status = "ready"

                yield  # yield 前是启动阶段；yield 后进入资源释放阶段。
            finally:
                await session_memory_store.aclose()
                await vector_store.aclose()

    application = FastAPI(
        title="Vehicle Diagnostic Agent API",
        version="0.1.0",
        description="Typed API boundary for the vehicle diagnostic Agent backend.",
        lifespan=lifespan,
    )
    application.include_router(qa_router)

    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
    )
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return application


app = create_app()
