from pydantic import BaseModel, ConfigDict, Field


class GeneratedVehicleAnswer(BaseModel):
    # LEARNING: 模型只生成叙述字段；severity/confidence 由服务端流程决定。
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    answer: str = Field(min_length=1, max_length=4000)
    findings: list[str] = Field(default_factory=list, max_length=10)
    recommendations: list[str] = Field(default_factory=list, max_length=10)
