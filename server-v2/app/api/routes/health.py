import asyncio
import logging
from enum import Enum

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.contracts.health import HealthProbe

router = APIRouter(prefix="/health", tags=["system"])
_logger = logging.getLogger(__name__)


class ComponentStatus(str, Enum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"
    NOT_PROBED = "not_probed"


class ReadinessStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"


class ReadinessResponse(BaseModel):
    status: ReadinessStatus
    components: dict[str, ComponentStatus]


async def _probe(name: str, component: object, timeout_seconds: float) -> ComponentStatus:
    if not isinstance(component, HealthProbe):
        return ComponentStatus.NOT_PROBED
    try:
        # 每个探测单独限时，一个卡住的依赖不能拖住整个健康检查。
        async with asyncio.timeout(timeout_seconds):
            await component.ping()
    except Exception as exc:  # noqa: BLE001 - any probe failure means unavailable
        _logger.warning("health_probe_failed component=%s type=%s", name, type(exc).__name__)
        return ComponentStatus.UNAVAILABLE
    return ComponentStatus.OK


def _configured(component: object) -> ComponentStatus:
    # 模型只看配置，不在探测时真正调用：推理慢且可能计费。
    return ComponentStatus.OK if component is not None else ComponentStatus.NOT_CONFIGURED


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse:
    state = request.app.state
    timeout_seconds = state.settings.health_probe_timeout_seconds
    session_memory, vector_store = await asyncio.gather(
        _probe("session_memory", state.session_memory_store, timeout_seconds),
        _probe("vector_store", state.vector_store, timeout_seconds),
    )
    components = {
        "session_memory": session_memory,
        "vector_store": vector_store,
        "chat_model": _configured(state.chat_model),
        "embedding_model": _configured(state.embedding_model),
    }
    # LEARNING: 依赖故障时服务仍能给出规则兜底，所以返回 200 + degraded，
    # 而不是 503 让负载均衡摘除流量。not_configured 是有意配置，不算降级。
    degraded = ComponentStatus.UNAVAILABLE in components.values()
    return ReadinessResponse(
        status=ReadinessStatus.DEGRADED if degraded else ReadinessStatus.READY,
        components=components,
    )
