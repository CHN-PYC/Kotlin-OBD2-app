from app.agent.nodes import (
    BuildPromptNode,
    BuildResponseNode,
    EvidenceGateNode,
    GenerateModelNode,
    ParseModelOutputNode,
    PrepareBaselineNode,
    RetrieveEvidenceNode,
    RewriteQueryNode,
    RuleFallbackNode,
)
from app.agent.state import AgentPhase, VehicleAgentState
from app.schemas.memory import SessionMemory
from app.schemas.qa import VehicleQARequest


class WorkFlow:
    def __init__(
        self,
        prepare_node: PrepareBaselineNode,
        prompt_node: BuildPromptNode,
        generate_node: GenerateModelNode,
        fallback_node: RuleFallbackNode,
        parse_node: ParseModelOutputNode,
        response_node: BuildResponseNode,
        retrieval_node: RetrieveEvidenceNode | None = None,
        evidence_gate_node: EvidenceGateNode | None = None,
        rewrite_node: RewriteQueryNode | None = None,
    ) -> None:
        self._prepare_node = prepare_node
        self._prompt_node = prompt_node
        self._generate_node = generate_node
        self._fallback_node = fallback_node
        self._parse_node = parse_node
        self._response_node = response_node
        self._retrieval_node = retrieval_node
        self._evidence_gate_node = evidence_gate_node
        self._rewrite_node = rewrite_node

    async def run(
        self,
        request: VehicleQARequest,
        *,
        session_memory: SessionMemory | None = None,
    ) -> VehicleAgentState:
        # LEARNING: 每次 run 创建独立状态；不要把当前 State 保存到共享的 self 上。
        state = VehicleAgentState(
            request=request,
            session_memory=session_memory or SessionMemory(session_id=request.session_id),
        )
        state = await self._prepare_node.run(state)
        if self._rewrite_node is not None:
            state = self._rewrite_node.run(state)
        else:
            state = state.model_copy(update={"rewritten_query": request.question})
        if self._retrieval_node is not None:
            if self._evidence_gate_node is None:
                raise RuntimeError("retrieval workflow requires an evidence gate")
            state = await self._retrieval_node.run(state)
            if state.phase is AgentPhase.FALLBACK:
                return self._fallback_node.run(state)
            state = self._evidence_gate_node.run(state)
            if state.phase is AgentPhase.FALLBACK:
                return self._fallback_node.run(state)
        state = self._prompt_node.run(state)
        if state.phase is AgentPhase.FALLBACK:
            return self._fallback_node.run(state)
        state = await self._generate_node.run(state)

        if state.phase is AgentPhase.FALLBACK:
            # LEARNING: return 结束本次调度，避免失败后继续执行解析节点。
            return self._fallback_node.run(state)

        state = self._parse_node.run(state)

        if state.phase is AgentPhase.FALLBACK:
            return self._fallback_node.run(state)

        return self._response_node.run(state)
