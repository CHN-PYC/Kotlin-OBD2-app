import logging

from app.schemas.agent_trace import AgentTraceStep, TraceStatus
from app.schemas.qa import VehicleQARequest, VehicleQAResponse
from app.services.generation.qa_service import RuleFallbackQAService, VehicleQAService


class ExceptionFallbackQAService:
    """Last safety net: unexpected errors become a rule answer instead of HTTP 500."""

    def __init__(
        self,
        delegate: VehicleQAService,
        *,
        fallback: VehicleQAService | None = None,
    ) -> None:
        self._delegate = delegate
        self._fallback = fallback if fallback is not None else RuleFallbackQAService()
        self._logger = logging.getLogger(__name__)

    async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
        try:
            return await self._delegate.answer(request)
        except Exception as exc:  # noqa: BLE001 - deliberate last-resort boundary
            # LEARNING: Exception 不包含 asyncio.CancelledError（BaseException），
            # 客户端断开或服务关闭时的取消会继续向上传播。
            # 只记录类型名：异常消息可能包含用户问题或内部地址。
            self._logger.warning("qa_unexpected_error type=%s", type(exc).__name__)
        # 兜底本身失败时不再捕获，交给 FastAPI 返回 500，避免无限嵌套。
        response = await self._fallback.answer(request)
        return response.model_copy(
            update={
                "agent_trace": [
                    AgentTraceStep(
                        step="unexpected_error",
                        status=TraceStatus.FAILED,
                        detail="Unexpected service error; returned rule fallback.",
                    ),
                    *response.agent_trace,
                ],
            }
        )
