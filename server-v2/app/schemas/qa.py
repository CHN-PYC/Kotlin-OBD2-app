from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent_trace import AgentTraceStep
from app.schemas.generation import ClaimKind
from app.schemas.retrieval import RetrievedSource
from app.schemas.rule_summary import DiagnosticSeverity, RuleSummary
from app.schemas.vehicle_context import VehicleContext


class AnswerMode(str, Enum):
    LLM_ONLY = "llm_only"
    LLM_RAG = "llm_rag"
    RULE_FALLBACK = "rule_fallback"
    INSUFFICIENT_RETRIEVAL_EVIDENCE = "insufficient_retrieval_evidence"
    LLM_NOT_CONFIGURED = "llm_not_configured"
    LLM_CALL_FAILED = "llm_call_failed"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimSupport(str, Enum):
    # cited 只表示引用的片段确实在本次证据中，不表示片段一定支持该说法。
    CITED = "cited"
    UNSUPPORTED = "unsupported"


class ResponseClaim(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    kind: ClaimKind
    support: ClaimSupport
    source_chunk_ids: list[str] = Field(default_factory=list)


class VehicleQARequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", strict=True)
    vehicle_context: VehicleContext
    # LEARNING: T | None 表示字段可为空，但不等于可以传任意类型。
    rule_summary: RuleSummary | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=1000)


class VehicleQAResponse(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    answer: str = Field(min_length=1)
    severity: DiagnosticSeverity
    # LEARNING: default_factory 每次创建新列表，避免多个响应共享可变默认值。
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    claims: list[ResponseClaim] = Field(default_factory=list)
    sources: list[RetrievedSource] = Field(default_factory=list)
    rewritten_query: str = Field(min_length=1)
    answer_mode: AnswerMode
    confidence: ConfidenceLevel
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)
