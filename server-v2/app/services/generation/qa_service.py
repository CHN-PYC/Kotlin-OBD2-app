from typing import Protocol

from app.providers.chat import ChatModel
from app.providers.errors import InvalidModelResponseError, ModelProviderError
from app.schemas.agent_trace import AgentTraceStep, TraceStatus
from app.schemas.qa import AnswerMode, ConfidenceLevel, VehicleQARequest, VehicleQAResponse
from app.schemas.rule_summary import DiagnosticSeverity
from app.services.generation.answer_parser import VehicleAnswerParser
from app.services.generation.prompt_builder import VehicleQAPromptBuilder


class VehicleQAService(Protocol):
    async def answer(self, request: VehicleQARequest) -> VehicleQAResponse: ...


class RuleFallbackQAService:
    async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
        rule_summary = request.rule_summary
        severity = rule_summary.severity if rule_summary is not None else DiagnosticSeverity.NOTICE
        findings = (
            [f"{finding.title}: {finding.detail}" for finding in rule_summary.findings]
            if rule_summary is not None
            else []
        )
        recommendations = list(rule_summary.recommendations) if rule_summary is not None else []
        answer = (
            rule_summary.summary
            if rule_summary is not None
            else "No rule diagnosis is available; collect more vehicle data before diagnosis."
        )

        return VehicleQAResponse(
            answer=answer,
            severity=severity,
            findings=findings,
            recommendations=recommendations,
            sources=[],
            rewritten_query=request.question,
            answer_mode=AnswerMode.RULE_FALLBACK,
            confidence=ConfidenceLevel.LOW,
            agent_trace=[
                AgentTraceStep(
                    step="rule_fallback",
                    status=TraceStatus.FALLBACK,
                    detail="Returned deterministic rule evidence.",
                )
            ],
        )


class LLMVehicleQAService:
    def __init__(
        self,
        *,
        model: ChatModel,
        prompt_builder: VehicleQAPromptBuilder,
        fallback: VehicleQAService,
        answer_parser: VehicleAnswerParser,
    ) -> None:
        self._model = model
        self._prompt_builder = prompt_builder
        self._fallback = fallback
        self._answer_parser = answer_parser

    async def answer(
        self,
        request: VehicleQARequest,
    ) -> VehicleQAResponse:
        # LEARNING: baseline 是随时可返回的确定性规则答案，不代表已经发生降级。
        baseline = await self._fallback.answer(request)
        chat_request = self._prompt_builder.build(request)

        try:
            # LEARNING: async 方法不 await 只会得到 coroutine，而不是 ChatResult。
            result = await self._model.generate(chat_request)
        except ModelProviderError as exc:
            # LEARNING: model_copy 创建新对象，baseline 保持不变；update 不重新校验外部数据。
            return baseline.model_copy(
                update={
                    "answer_mode": AnswerMode.LLM_CALL_FAILED,
                    "confidence": ConfidenceLevel.LOW,
                    "agent_trace": [
                        AgentTraceStep(
                            step="model_generation",
                            status=TraceStatus.FAILED,
                            detail=f"Model provider failed with {exc.code}.",
                        ),
                        AgentTraceStep(
                            step="rule_fallback",
                            status=TraceStatus.FALLBACK,
                            detail="Returned deterministic rule evidence.",
                        ),
                    ],
                }
            )

        # LEARNING: length 表示输出被截断，有文本也不能视为完整诊断。
        if result.finish_reason != "stop":
            return baseline.model_copy(
                update={
                    "answer_mode": AnswerMode.LLM_CALL_FAILED,
                    "confidence": ConfidenceLevel.LOW,
                    "agent_trace": [
                        AgentTraceStep(
                            step="model_generation",
                            status=TraceStatus.FAILED,
                            detail=(
                                f"Model stopped with finish_reason={result.finish_reason}; "
                                "answer discarded."
                            ),
                        ),
                        AgentTraceStep(
                            step="rule_fallback",
                            status=TraceStatus.FALLBACK,
                            detail="Returned deterministic rule evidence.",
                        ),
                    ],
                }
            )
        try:
            generated_answer = self._answer_parser.parse(result)
        except InvalidModelResponseError as exc:
            return baseline.model_copy(
                update={
                    "answer_mode": AnswerMode.LLM_CALL_FAILED,
                    "confidence": ConfidenceLevel.LOW,
                    "agent_trace": [
                        AgentTraceStep(
                            step="model_output_parse",
                            status=TraceStatus.FAILED,
                            detail=f"Model output parsing failed with {exc.code}.",
                        ),
                        AgentTraceStep(
                            step="rule_fallback",
                            status=TraceStatus.FALLBACK,
                            detail="Returned deterministic rule evidence.",
                        ),
                    ],
                }
            )
        confidence = (
            ConfidenceLevel.MEDIUM if request.rule_summary is not None else ConfidenceLevel.LOW
        )
        return baseline.model_copy(
            update={
                "answer": generated_answer.answer,
                "answer_mode": AnswerMode.LLM_ONLY,
                "confidence": confidence,
                "findings": list(generated_answer.findings),
                "recommendations": list(generated_answer.recommendations),
                "agent_trace": [
                    AgentTraceStep(
                        step="prompt_build",
                        status=TraceStatus.COMPLETED,
                        detail="Built structured vehicle evidence prompt.",
                    ),
                    AgentTraceStep(
                        step="model_generation",
                        status=TraceStatus.COMPLETED,
                        detail=f"Generated by {result.provider}/{result.model}.",
                    ),
                    AgentTraceStep(
                        step="model_output_parse",
                        status=TraceStatus.COMPLETED,
                        detail="Validated structured model output.",
                    ),
                ],
            }
        )
