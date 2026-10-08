import logging
import time

from app.agent.state import AgentPhase
from app.agent.workflow import WorkFlow
from app.contracts.session_memory import SessionMemoryStore
from app.schemas.memory import ConversationTurn, SessionMemory
from app.schemas.qa import VehicleQARequest, VehicleQAResponse
from app.services.memory.errors import SessionMemoryError


class WorkflowQAService:
    def __init__(
        self,
        *,
        workflow: WorkFlow,
        memory_store: SessionMemoryStore | None = None,
    ) -> None:
        self._workflow = workflow
        self._memory_store = memory_store
        self._logger = logging.getLogger(__name__)

    async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
        memory = await self._load_memory(request.session_id)
        state = await self._workflow.run(request, session_memory=memory)
        # LEARNING: 适配器把内部 State 转为 API 响应，避免把全部中间数据返回客户端。
        if state.phase is not AgentPhase.COMPLETED or state.final_response is None:
            raise RuntimeError("Workflow must complete with a final_response")
        response = state.final_response
        if self._memory_store is not None:
            try:
                await self._memory_store.append(
                    request.session_id,
                    ConversationTurn(
                        question=request.question,
                        rewritten_query=response.rewritten_query,
                        answer=response.answer,
                        answer_mode=response.answer_mode,
                        created_at=int(time.time()),
                    ),
                )
            except SessionMemoryError as exc:
                # Memory is non-critical: diagnosis must still return. Do not log
                # question, answer, session ID, or provider credentials.
                self._logger.warning("session_memory_append_failed type=%s", type(exc).__name__)
        return response

    async def _load_memory(self, session_id: str) -> SessionMemory:
        if self._memory_store is None:
            return SessionMemory(session_id=session_id)
        try:
            return await self._memory_store.load(session_id)
        except SessionMemoryError as exc:
            self._logger.warning("session_memory_load_failed type=%s", type(exc).__name__)
            return SessionMemory(session_id=session_id)
