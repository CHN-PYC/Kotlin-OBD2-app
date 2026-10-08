import asyncio
import math

from app.schemas.agent_trace import AgentTraceStep, TraceStatus
from app.schemas.qa import VehicleQARequest, VehicleQAResponse
from app.services.generation.qa_service import RuleFallbackQAService, VehicleQAService


class DeadlineQAService:
    """Bound async workflow work, including retries and memory I/O."""

    def __init__(self, delegate: VehicleQAService, *, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("deadline must be finite and positive")
        self._delegate = delegate
        self._seconds = seconds

    async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
        deadline = asyncio.timeout(self._seconds)
        try:
            async with deadline:
                return await self._delegate.answer(request)
        except TimeoutError:
            # A dependency's own TimeoutError is not a request deadline expiry.
            if not deadline.expired():
                raise
            response = await RuleFallbackQAService().answer(request)
            return response.model_copy(
                update={
                    "agent_trace": [
                        AgentTraceStep(
                            step="request_deadline",
                            status=TraceStatus.FAILED,
                            detail="Request time budget exhausted; pending async work cancelled.",
                        ),
                        *response.agent_trace,
                    ],
                }
            )
