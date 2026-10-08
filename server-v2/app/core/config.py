from enum import Enum
from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class VectorStoreProvider(str, Enum):
    MEMORY = "memory"
    QDRANT = "qdrant"


class RerankerProvider(str, Enum):
    PASS_THROUGH = "pass_through"
    FASTEMBED = "fastembed"


class RetrievalMode(str, Enum):
    DENSE = "dense"
    HYBRID = "hybrid"


class SessionMemoryProvider(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VEHICLE_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )
    # LEARNING: SecretStr 避免密钥在 repr/log 中被直接打印，不代表已经完成鉴权。
    api_key: SecretStr | None = None
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8000, ge=1, le=65535)
    model_provider: ModelProvider = ModelProvider.OLLAMA
    llm_base_url: AnyHttpUrl | None = None
    llm_model: str | None = Field(default=None, min_length=1)
    # LEARNING: 远程模型密钥与 Android 调用本服务的 api_key 是两种凭证。
    llm_api_key: SecretStr | None = None
    llm_json_mode: bool = False
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:11434/")
    ollama_chat_model: str | None = Field(default=None, min_length=1)
    ollama_embedding_model: str | None = Field(default=None, min_length=1)
    ollama_embedding_num_gpu: int | None = Field(default=None, ge=0)
    embedding_batch_size: int = Field(default=16, ge=1, le=128)
    model_timeout_seconds: float = Field(default=30, gt=0)
    model_max_output_tokens: int = Field(default=512, ge=1, le=8192)

    model_max_attempts: int = Field(default=3, ge=1, le=5)
    model_retry_base_delay_seconds: float = Field(default=0.1, ge=0, allow_inf_nan=False)
    request_deadline_seconds: float = Field(default=60, gt=0, allow_inf_nan=False)
    model_circuit_failure_threshold: int = Field(default=5, ge=1)
    model_circuit_recovery_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)

    vector_store_provider: VectorStoreProvider = VectorStoreProvider.MEMORY
    embedding_dimension: int = Field(default=1024, ge=1)
    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:6333/")
    qdrant_collection_name: str = Field(
        default="vehicle_knowledge_v1",
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    )
    qdrant_timeout_seconds: int = Field(default=10, ge=1)
    qdrant_api_key: SecretStr | None = None
    rag_candidate_multiplier: int = Field(default=2, ge=1, le=5)
    retrieval_mode: RetrievalMode = RetrievalMode.DENSE
    evidence_min_dense_score: float = Field(default=0.35, ge=-1, le=1, allow_inf_nan=False)
    reranker_provider: RerankerProvider = RerankerProvider.PASS_THROUGH
    reranker_model: str = Field(default="BAAI/bge-reranker-base", min_length=1)
    reranker_batch_size: int = Field(default=8, ge=1, le=64)
    reranker_threads: int | None = Field(default=None, ge=1)
    session_memory_provider: SessionMemoryProvider = SessionMemoryProvider.MEMORY
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", min_length=1)
    session_ttl_seconds: int = Field(default=1800, ge=60, le=604800)
    session_max_turns: int = Field(default=10, ge=1, le=50)
    context_max_characters: int = Field(default=16000, ge=2000, le=100000)
    context_max_history_turns: int = Field(default=6, ge=0, le=20)


@lru_cache
def get_settings() -> Settings:
    # LEARNING: 缓存避免每次依赖解析都重新读取环境变量；测试可直接注入 Settings。
    return Settings()
