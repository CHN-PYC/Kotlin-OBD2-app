import asyncio
from collections.abc import Awaitable, Callable

from app.providers.chat import ChatModel, ChatRequest, ChatResult
from app.providers.errors import ModelProviderError

# LEARNING: 可注入 sleep 后，测试可记录等待时间而不必真的休眠。
Sleep = Callable[[float], Awaitable[None]]


class RetryingChatModel:
    def __init__(
        self,
        delegate: ChatModel,
        max_attempts: int = 3,
        base_delay_seconds: float = 0.1,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if not 1 <= max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative")
        self.delegate = delegate
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.sleep = sleep
        self.provider_name = delegate.provider_name
        self.model_name = delegate.model_name

    async def generate(self, request: ChatRequest) -> ChatResult:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await self.delegate.generate(request)
            except ModelProviderError as exc:
                if not exc.retryable:
                    raise
                if attempt == self.max_attempts:
                    raise
                # LEARNING: 指数退避为 base、2*base、4*base；只重试 retryable 错误。
                delay = self.base_delay_seconds * (2 ** (attempt - 1))
                await self.sleep(delay)
        raise AssertionError("unreachable")
