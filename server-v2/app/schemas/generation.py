from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ClaimKind(str, Enum):
    DEFINITION = "definition"
    CAUSE = "cause"
    CHECK = "check"


class GeneratedClaim(BaseModel):
    # LEARNING: 一条 claim 只表达一个可核查的说法，便于用户逐条接受或拒绝。
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    text: str = Field(min_length=1, max_length=500)
    kind: ClaimKind
    # 模型声称的引用只是提议；服务端会对照本次实际发送的证据重新校验。
    source_chunk_ids: list[str] = Field(default_factory=list, max_length=3)
    # 逐字摘录的支持句；服务端只在它确实出现在所引片段中时才展示。
    quote: str | None = Field(default=None, max_length=400)
    # 依据来自车辆上下文或规则摘要，而不是检索文档。
    uses_vehicle_data: bool = False


class GeneratedVehicleAnswer(BaseModel):
    # LEARNING: 模型只生成叙述字段；severity/confidence 由服务端流程决定。
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    answer: str = Field(min_length=1, max_length=4000)
    claims: list[GeneratedClaim] = Field(default_factory=list, max_length=10)
