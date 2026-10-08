import httpx2
from qdrant_client import AsyncQdrantClient

from app.contracts.vector_store import VectorStore
from app.core.config import ModelProvider, RerankerProvider, Settings, VectorStoreProvider
from app.providers.chat import ChatModel
from app.providers.circuit_breaker import CircuitBreakerChatModel
from app.providers.embedding import EmbeddingModel
from app.providers.fastembed_reranker import FastEmbedCrossEncoder
from app.providers.ollama import OllamaChatModel
from app.providers.ollama_embedding import OllamaEmbeddingModel
from app.providers.openai_compatible import OpenAICompatibleChatModel
from app.providers.qdrant_vector_store import QdrantVectorStore
from app.providers.retry import RetryingChatModel
from app.services.retrieval.memory_vector_store import MemoryVectorStore
from app.services.retrieval.reranking import (
    CrossEncoderReranker,
    PassThroughReranker,
    Reranker,
    ResilientReranker,
)


def create_chat_model(
    settings: Settings,
    *,
    client: httpx2.AsyncClient | None = None,
) -> ChatModel:
    model: ChatModel
    if settings.model_provider is ModelProvider.OLLAMA:
        model = OllamaChatModel(
            base_url=str(settings.ollama_base_url),
            model_name=settings.ollama_chat_model,
            timeout_seconds=settings.model_timeout_seconds,
            client=client,
        )
    else:
        model = OpenAICompatibleChatModel(
            base_url=str(settings.llm_base_url) if settings.llm_base_url else None,
            model_name=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.model_timeout_seconds,
            json_mode=settings.llm_json_mode,
            client=client,
        )
    return CircuitBreakerChatModel(
        RetryingChatModel(
            model,
            max_attempts=settings.model_max_attempts,
            base_delay_seconds=settings.model_retry_base_delay_seconds,
        ),
        failure_threshold=settings.model_circuit_failure_threshold,
        recovery_seconds=settings.model_circuit_recovery_seconds,
    )


def create_embedding_model(
    settings: Settings,
    *,
    client: httpx2.AsyncClient | None = None,
) -> EmbeddingModel:
    return OllamaEmbeddingModel(
        base_url=str(settings.ollama_base_url),
        model_name=settings.ollama_embedding_model,
        expected_dimension=settings.embedding_dimension,
        timeout_seconds=settings.model_timeout_seconds,
        num_gpu=settings.ollama_embedding_num_gpu,
        client=client,
    )


def create_reranker(settings: Settings) -> Reranker:
    fallback = PassThroughReranker()
    if settings.reranker_provider is RerankerProvider.PASS_THROUGH:
        return fallback
    if settings.reranker_provider is not RerankerProvider.FASTEMBED:
        raise ValueError(f"Unsupported reranker provider: {settings.reranker_provider}")
    primary = CrossEncoderReranker(
        FastEmbedCrossEncoder(
            model_name=settings.reranker_model,
            batch_size=settings.reranker_batch_size,
            threads=settings.reranker_threads,
        )
    )
    return ResilientReranker(primary, fallback)


async def create_vector_store(
    settings: Settings,
    *,
    client: AsyncQdrantClient | None = None,
) -> VectorStore:
    if settings.vector_store_provider is VectorStoreProvider.MEMORY:
        return MemoryVectorStore(dimension=settings.embedding_dimension)
    if settings.vector_store_provider is not VectorStoreProvider.QDRANT:
        raise ValueError(f"Unsupported vector store provider: {settings.vector_store_provider}")

    api_key = (
        settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key is not None else None
    )
    store = QdrantVectorStore(
        url=str(settings.qdrant_url),
        collection_name=settings.qdrant_collection_name,
        dimension=settings.embedding_dimension,
        timeout_seconds=settings.qdrant_timeout_seconds,
        api_key=api_key,
        client=client,
    )
    try:
        await store.ensure_collection()
    except Exception:
        await store.aclose()
        raise
    return store
