from datetime import datetime, UTC
from uuid import uuid4
from app.models.qa_log import QaLog
from app.repositories.qa_log_repository import QaLogRepository
from app.schemas.qa import VehicleQaRequest, VehicleQaResponse
from app.services.llm_service import LlmService
from app.services.retrieval_service import RetrievalService


class RagService:
    def __init__(self) -> None:
        self.retrieval_service = RetrievalService()
        self.llm_service = LlmService()
        self.qa_log_repository = QaLogRepository()

    def answer(self, request: VehicleQaRequest) -> VehicleQaResponse:
        rewritten_query, sources = self.retrieval_service.retrieve(
            question=request.question,
            vehicle_context=request.vehicle_context,
            rule_summary=request.rule_summary,
            top_k=request.top_k,
        )
        result = self.llm_service.answer_question(
            question=request.question,
            vehicle_context=request.vehicle_context,
            rule_summary=request.rule_summary,
            sources=sources,
            rewritten_query=rewritten_query,
        )
        response = VehicleQaResponse(
            answer=result["answer"],
            severity=result["severity"],
            findings=result["findings"],
            recommendations=result["recommendations"],
            sources=sources,
            rewritten_query=rewritten_query,
        )
        self.qa_log_repository.save(
            QaLog(
                qa_id=str(uuid4()),
                session_id=request.session_id,
                question=request.question,
                rewritten_query=rewritten_query,
                retrieved_chunk_ids=[item.chunk_id for item in sources],
                answer=response.answer,
                severity=response.severity,
                sources=[item.source_url for item in sources],
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        return response
