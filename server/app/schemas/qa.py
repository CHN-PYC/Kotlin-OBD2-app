from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from .common import RetrievedSource


class VehicleQaRequest(BaseModel):
    session_id: str
    question: str
    vehicle_context: Dict[str, Any]
    rule_summary: Optional[Dict[str, Any]] = None
    top_k: int = Field(default=5, ge=1, le=20)


class VehicleQaResponse(BaseModel):
    answer: str
    severity: str
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    sources: List[RetrievedSource] = Field(default_factory=list)
    rewritten_query: str
