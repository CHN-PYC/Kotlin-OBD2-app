from pydantic import BaseModel, ConfigDict, Field


class QueryRewriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    original_query: str = Field(min_length=1, max_length=1000)
    rewritten_query: str = Field(min_length=1, max_length=500)
    applied_rules: list[str] = Field(default_factory=list)
