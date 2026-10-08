from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DiagnosticSeverity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    NOTICE = "NOTICE"
    HIGH = "HIGH"


class RuleFinding(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    code: str = Field(min_length=1)
    severity: DiagnosticSeverity
    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class RuleSummary(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    severity: DiagnosticSeverity
    summary: str = Field(min_length=1)
    findings: list[RuleFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
