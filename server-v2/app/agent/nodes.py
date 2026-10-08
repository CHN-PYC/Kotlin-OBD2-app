from app.agent.state import AgentPhase, VehicleAgentState
from app.providers.chat import ChatModel
from app.providers.errors import InvalidModelResponseError, ModelProviderError
from app.providers.vector_store_errors import VectorStoreProviderError
from app.schemas.agent_trace import AgentTraceStep, TraceStatus
from app.schemas.qa import AnswerMode, ConfidenceLevel
from app.services.generation.answer_parser import VehicleAnswerParser
from app.services.generation.context_manager import ContextBudgetExceededError
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.generation.qa_service import VehicleQAService
from app.services.retrieval.query_retrieval import QueryRetrievalService
from app.services.retrieval.query_rewrite import DeterministicQueryRewriter
from app.tools.registry import ToolRegistry, ToolRegistryError
from app.tools.vehicle import KnowledgeSearchOutput


class RetrieveEvidenceNode:
    def __init__(
        self,
        *,
        retrieval_service: QueryRetrievalService | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        if (retrieval_service is None) == (tool_registry is None):
            raise ValueError("configure exactly one retrieval service or tool registry")
        self._retrieval_service = retrieval_service
        self._tool_registry = tool_registry

    async def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.BASELINE_PREPARED:
            raise ValueError("retrieval requires phase=baseline_prepared")
        try:
            query = state.rewritten_query or state.request.question
            if self._tool_registry is not None:
                result = await self._tool_registry.invoke(
                    "search_vehicle_knowledge",
                    {"query": query, "top_k": state.request.top_k},
                )
                sources = KnowledgeSearchOutput.model_validate(result).sources
            else:
                assert self._retrieval_service is not None
                sources = await self._retrieval_service.retrieve(
                    query,
                    final_k=state.request.top_k,
                )
        except (ModelProviderError, VectorStoreProviderError, ToolRegistryError) as exc:
            failure_code = getattr(exc, "code", exc.__class__.__name__.lower())
            return state.model_copy(
                update={
                    "phase": AgentPhase.FALLBACK,
                    "failure_code": f"retrieval_{failure_code}",
                    "trace": [
                        *state.trace,
                        AgentTraceStep(
                            step="retrieval_tool",
                            status=TraceStatus.FAILED,
                            detail=f"Retrieval tool failed with {failure_code}.",
                        ),
                    ],
                }
            )
        return state.model_copy(
            update={
                "phase": AgentPhase.EVIDENCE_RETRIEVED,
                "reranked_sources": list(sources),
                "trace": [
                    *state.trace,
                        AgentTraceStep(
                            step="retrieval_tool",
                            status=TraceStatus.COMPLETED,
                            detail=(
                                f"Retrieved {len(sources)} evidence chunks; "
                                f"reranker={sources[0].rerank_provider if sources else 'skipped'}."
                            ),
                        ),
                ],
            }
        )


class RewriteQueryNode:
    def __init__(self, *, rewriter: DeterministicQueryRewriter) -> None:
        self._rewriter = rewriter

    def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.BASELINE_PREPARED:
            raise ValueError("query rewrite requires phase=baseline_prepared")
        memory = state.session_memory
        if memory is None:
            raise ValueError("query rewrite requires session_memory")
        result = self._rewriter.rewrite(state.request, memory)
        return state.model_copy(
            update={
                "rewritten_query": result.rewritten_query,
                "trace": [
                    *state.trace,
                    AgentTraceStep(
                        step="query_rewrite",
                        status=TraceStatus.COMPLETED,
                        detail=(
                            f"Applied {len(result.applied_rules)} deterministic rewrite rules."
                        ),
                    ),
                ],
            }
        )


class EvidenceGateNode:
    def __init__(self, *, min_dense_score: float) -> None:
        if not -1 <= min_dense_score <= 1:
            raise ValueError("min_dense_score must be between -1 and 1")
        self._min_dense_score = min_dense_score

    def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.EVIDENCE_RETRIEVED:
            raise ValueError("evidence gate requires phase=evidence_retrieved")
        best_score = max(
            (item.source.score for item in state.reranked_sources),
            default=None,
        )
        if best_score is None or best_score < self._min_dense_score:
            return state.model_copy(
                update={
                    "phase": AgentPhase.FALLBACK,
                    "failure_code": "insufficient_retrieval_evidence",
                    "trace": [
                        *state.trace,
                        AgentTraceStep(
                            step="evidence_gate",
                            status=TraceStatus.FALLBACK,
                            detail="Retrieval evidence did not meet the configured threshold.",
                        ),
                    ],
                }
            )
        return state.model_copy(
            update={
                "phase": AgentPhase.EVIDENCE_ACCEPTED,
                "trace": [
                    *state.trace,
                    AgentTraceStep(
                        step="evidence_gate",
                        status=TraceStatus.PASSED,
                        detail=(
                            f"Accepted {len(state.reranked_sources)} chunks; "
                            f"best dense score={best_score:.3f}."
                        ),
                    ),
                ],
            }
        )


class PrepareBaselineNode:
    # LEARNING: 参数中的 * 要求后续参数按名称传入，例如 fallback=service。
    def __init__(self, *, fallback: VehicleQAService) -> None:
        self._fallback = fallback

    async def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.RECEIVED:
            raise ValueError("prepare_baseline requires phase=received")
        baseline = await self._fallback.answer(state.request)

        return state.model_copy(
            update={
                "phase": AgentPhase.BASELINE_PREPARED,
                "baseline_response": baseline,
                "trace": [
                    # LEARNING: * 展开旧列表元素；新列表保留历史，再追加本次记录。
                    # 这是浅复制，旧记录对象仍共享；不要原地修改旧记录。
                    *state.trace,
                    AgentTraceStep(
                        step="prepare_baseline",
                        status=TraceStatus.COMPLETED,
                        detail="Prepared deterministic rule fallback response.",
                    ),
                ],
            }
        )


class BuildPromptNode:
    def __init__(self, *, prompt_builder: VehicleQAPromptBuilder) -> None:
        self._prompt_builder = prompt_builder

    def run(self, state: VehicleAgentState) -> VehicleAgentState:
        # LEARNING: 阶段和数据分别校验；改了 phase 不代表 baseline 已经准备好。
        if state.phase not in {AgentPhase.BASELINE_PREPARED, AgentPhase.EVIDENCE_ACCEPTED}:
            raise ValueError(
                "build prompt requires phase=baseline_prepared or evidence_accepted"
            )
        if state.baseline_response is None:
            raise ValueError("build prompt requires baseline_response ")
        # LEARNING: build 只做内存中的数据转换，普通 def 即可，不需要 await。
        try:
            chat_request, selected_sources = self._prompt_builder.build_with_selection(
                state.request,
                sources=[item.source for item in state.reranked_sources],
                rewritten_query=state.rewritten_query,
                history=state.session_memory.turns if state.session_memory is not None else [],
            )
        except ContextBudgetExceededError:
            return state.model_copy(
                update={
                    "phase": AgentPhase.FALLBACK,
                    "failure_code": "context_budget_exceeded",
                    "trace": [
                        *state.trace,
                        AgentTraceStep(
                            step="prompt_build",
                            status=TraceStatus.FAILED,
                            detail="Mandatory context exceeded the configured budget.",
                        ),
                    ],
                }
            )
        selected_ids = {source.chunk_id for source in selected_sources}
        return state.model_copy(
            update={
                "phase": AgentPhase.PROMPT_BUILT,
                "chat_request": chat_request,
                "reranked_sources": [
                    item for item in state.reranked_sources if item.source.chunk_id in selected_ids
                ],
                "trace": [
                    *state.trace,
                    AgentTraceStep(
                        step="prompt_build",
                        status=TraceStatus.COMPLETED,
                        detail=(
                            f"Built prompt with {len(selected_sources)} evidence chunks and "
                            f"{len(state.session_memory.turns) if state.session_memory else 0} "
                            "available history turns."
                        ),
                    ),
                ],
            }
        )


class GenerateModelNode:
    def __init__(self, *, model: ChatModel) -> None:
        self._model = model

    async def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.PROMPT_BUILT:
            raise ValueError("generate model requires phase=prompt_built")
        if state.chat_request is None:
            raise ValueError("generate_mode requires chat_request")
        if state.baseline_response is None:
            raise ValueError("generate model requires baseline_response")
        try:
            result = await self._model.generate(state.chat_request)
        except ModelProviderError as exc:
            return state.model_copy(
                update={
                    "phase": AgentPhase.FALLBACK,
                    "chat_result": None,
                    "failure_code": exc.code,
                    "trace": [
                        *state.trace,
                        AgentTraceStep(
                            step="model_generation",
                            status=TraceStatus.FAILED,
                            detail=f"Generation failed: {exc.code}.",
                        ),
                    ],
                }
            )
        return state.model_copy(
            update={
                "phase": AgentPhase.MODEL_GENERATED,
                "chat_result": result,
                "failure_code": None,
                "trace": [
                    *state.trace,
                    AgentTraceStep(
                        step="model_generation",
                        status=TraceStatus.COMPLETED,
                        detail=self._model.model_name,
                    ),
                ],
            }
        )


class ParseModelOutputNode:
    def __init__(self, *, answer_parser: VehicleAnswerParser) -> None:
        self._answer_parser = answer_parser

    def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.MODEL_GENERATED:
            raise ValueError("parse output requires phase=model_generated")
        if state.chat_result is None or state.baseline_response is None:
            raise ValueError("parse output requires chat_result and baseline_response")
        result = state.chat_result
        try:
            # LEARNING: 完整生成与 JSON 合法是两个条件，先检查结束原因。
            if result.finish_reason != "stop":
                raise InvalidModelResponseError(
                    f"finish_reason={result.finish_reason}",
                    provider=result.provider,
                    model=result.model,
                )
            generated = self._answer_parser.parse(result)
        except InvalidModelResponseError as exc:
            detail = (
                f"finish_reason={result.finish_reason}"
                if result.finish_reason != "stop"
                else exc.code
            )
            return state.model_copy(
                update={
                    "phase": AgentPhase.FALLBACK,
                    "failure_code": exc.code,
                    "generated_answer": None,
                    "trace": [
                        *state.trace,
                        AgentTraceStep(
                            step="model_output_parse",
                            status=TraceStatus.FAILED,
                            detail=detail,
                        ),
                    ],
                }
            )
        return state.model_copy(
            update={
                "phase": AgentPhase.OUTPUT_PARSED,
                "generated_answer": generated,
                "trace": [
                    *state.trace,
                    AgentTraceStep(
                        step="model_output_parse",
                        status=TraceStatus.COMPLETED,
                        detail="Validated structured model output.",
                    ),
                ],
            }
        )


class BuildResponseNode:
    def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.OUTPUT_PARSED:
            raise ValueError("build response requires phase=output_parsed")
        if state.baseline_response is None or state.generated_answer is None:
            raise ValueError("build response requires baseline_response and generated_answer")
        generated = state.generated_answer
        trace = [
            *state.trace,
            AgentTraceStep(
                step="build_response",
                status=TraceStatus.COMPLETED,
                detail="Built final model-assisted response.",
            ),
        ]
        # LEARNING: Schema 通过只保证格式；此 confidence 是原流程的启发式标签。
        response = state.baseline_response.model_copy(
            update={
                "answer": generated.answer,
                "findings": list(generated.findings),
                "recommendations": list(generated.recommendations),
                "sources": [item.source.model_copy(deep=True) for item in state.reranked_sources],
                "answer_mode": (
                    AnswerMode.LLM_RAG if state.reranked_sources else AnswerMode.LLM_ONLY
                ),
                "confidence": (
                    ConfidenceLevel.MEDIUM
                    if state.request.rule_summary is not None
                    else ConfidenceLevel.LOW
                ),
                "rewritten_query": state.rewritten_query or state.request.question,
                "agent_trace": list(trace),
            }
        )
        return state.model_copy(
            update={
                "phase": AgentPhase.COMPLETED,
                "final_response": response,
                "trace": trace,
            }
        )


class RuleFallbackNode:
    def run(self, state: VehicleAgentState) -> VehicleAgentState:
        if state.phase is not AgentPhase.FALLBACK:
            raise ValueError("rule fallback requires phase=fallback")
        if state.baseline_response is None or not state.failure_code:
            raise ValueError("rule fallback requires baseline_response and failure_code")
        trace = [
            *state.trace,
            AgentTraceStep(
                step="rule_fallback",
                status=TraceStatus.FALLBACK,
                detail="Returned deterministic rule evidence.",
            ),
        ]
        response = state.baseline_response.model_copy(
            update={
                "answer_mode": (
                    AnswerMode.INSUFFICIENT_RETRIEVAL_EVIDENCE
                    if state.failure_code == "insufficient_retrieval_evidence"
                    else AnswerMode.LLM_CALL_FAILED
                    if not state.failure_code.startswith("retrieval_")
                    else AnswerMode.RULE_FALLBACK
                ),
                "confidence": ConfidenceLevel.LOW,
                "rewritten_query": state.rewritten_query or state.request.question,
                "agent_trace": list(trace),
            }
        )
        # LEARNING: completed 表示执行结束；降级结果由 answer_mode 和 trace 表达。
        return state.model_copy(
            update={
                "phase": AgentPhase.COMPLETED,
                "final_response": response,
                "trace": trace,
            }
        )
