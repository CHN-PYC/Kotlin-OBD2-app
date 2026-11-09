from typing import Protocol, runtime_checkable


@runtime_checkable
class HealthProbe(Protocol):
    """Optional capability: a cheap round trip proving the dependency is reachable."""

    # LEARNING: 单独定义而不是加进 VectorStore/SessionMemoryStore，
    # 已有实现和测试替身不必全部补 ping；没有 ping 的组件报告 not_probed。
    async def ping(self) -> None: ...
