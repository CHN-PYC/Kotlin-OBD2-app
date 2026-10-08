from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TraceStatus(str, Enum):
    COMPLETED = "completed"
    PASSED = "passed"
    FALLBACK = "fallback"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTraceStep(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # 设置去空格
    step: str = Field(min_length=1)  # Pydantic的Field，表示字符串长度不为0
    status: TraceStatus
    detail: str = ""
