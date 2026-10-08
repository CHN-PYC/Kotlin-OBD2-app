from pydantic import BaseModel, ConfigDict, Field

from app.schemas.qa import AnswerMode


class ConversationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=1000)
    rewritten_query: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=4000)
    answer_mode: AnswerMode
    created_at: int = Field(ge=0)


class SessionMemory(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    session_id: str = Field(min_length=1, max_length=128)
    turns: list[ConversationTurn] = Field(default_factory=list)
