from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.providers.chat import ChatRequest, ChatResult
from app.schemas.agent_trace import AgentTraceStep
from app.schemas.generation import GeneratedVehicleAnswer
from app.schemas.memory import SessionMemory
from app.schemas.qa import VehicleQARequest, VehicleQAResponse
from app.schemas.reranking import RerankedSource


class AgentPhase(str, Enum):
    RECEIVED = "received"
    BASELINE_PREPARED = "baseline_prepared"
    EVIDENCE_RETRIEVED = "evidence_retrieved"
    EVIDENCE_ACCEPTED = "evidence_accepted"
    PROMPT_BUILT = "prompt_built"
    MODEL_GENERATED = "model_generated"
    OUTPUT_PARSED = "output_parsed"
    COMPLETED = "completed"
    FALLBACK = "fallback"


class VehicleAgentState(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request: VehicleQARequest
    phase: AgentPhase = AgentPhase.RECEIVED
    rewritten_query: str | None = None
    session_memory: SessionMemory | None = None

    # LEARNING: baseline 是规则服务生成的备用响应，不是重复保存一份请求。
    baseline_response: VehicleQAResponse | None = None
    reranked_sources: list[RerankedSource] = Field(default_factory=list)
    chat_request: ChatRequest | None = None
    chat_result: ChatResult | None = None
    generated_answer: GeneratedVehicleAnswer | None = None
    final_response: VehicleQAResponse | None = None

    failure_code: str | None = None
    trace: list[AgentTraceStep] = Field(default_factory=list)
