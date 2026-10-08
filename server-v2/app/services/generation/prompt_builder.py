import json

from app.providers.chat import ChatMessage, ChatOptions, ChatRequest, ChatRole
from app.schemas.memory import ConversationTurn
from app.schemas.qa import VehicleQARequest
from app.schemas.retrieval import RetrievedSource
from app.services.generation.context_manager import ContextWindowManager


class VehicleQAPromptBuilder:
    def __init__(
        self,
        *,
        options: ChatOptions | None = None,
        context_manager: ContextWindowManager | None = None,
    ) -> None:
        self._options = options if options is not None else ChatOptions()
        self._context_manager = context_manager or ContextWindowManager()

    def build(
        self,
        request: VehicleQARequest,
        *,
        sources: list[RetrievedSource] | None = None,
        rewritten_query: str | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> ChatRequest:
        chat_request, _ = self.build_with_selection(
            request,
            sources=sources,
            rewritten_query=rewritten_query,
            history=history,
        )
        return chat_request

    def build_with_selection(
        self,
        request: VehicleQARequest,
        *,
        sources: list[RetrievedSource] | None = None,
        rewritten_query: str | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> tuple[ChatRequest, list[RetrievedSource]]:
        resolved_query = rewritten_query or request.question
        selection = self._context_manager.select(
            request,
            rewritten_query=resolved_query,
            sources=sources or [],
            history=history or [],
        )
        # LEARNING: model_dump 返回新 dict，不会原地修改 Pydantic 对象。
        prompt_data = {
            "question": request.question,
            "rewrittenQuery": resolved_query,
            "vehicleContext": request.vehicle_context.model_dump(mode="json", by_alias=True),
            "ruleSummary": request.rule_summary.model_dump(mode="json", by_alias=True)
            if request.rule_summary is not None
            else None,
            "retrievedEvidence": [
                source.model_dump(mode="json") for source in selection.sources
            ],
            "conversationHistory": [
                {
                    "question": turn.question,
                    "rewrittenQuery": turn.rewritten_query,
                    "answer": turn.answer,
                    "answerMode": turn.answer_mode.value,
                }
                for turn in selection.history
            ],
        }
        # LEARNING: json.dumps 返回标准 JSON 字符串；str(dict) 不是 JSON 协议。
        user_content = json.dumps(
            prompt_data,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        system_message = ChatMessage(
            role=ChatRole.SYSTEM,
            content=(
                "You are a cautious vehicle diagnostic assistant. Answer only from the "
                "provided evidence. If the evidence is insufficient, state the uncertainty "
                "and recommend safe next checks. Do not claim that a component is damaged "
                "without direct evidence. Conversation history may be stale; current vehicle "
                "context, rule summary, and retrieved evidence always take precedence. "
                'Return one JSON object with exactly these fields: "answer", "findings", '
                'and "recommendations". '
                '"answer" must be a nonempty string of at most 4000 characters. '
                '"findings" and "recommendations" must each be arrays of strings '
                "with at most 10 items, never arrays of objects. Use [] when empty. "
                "Do not wrap the JSON in Markdown code fences."
            ),
        )
        user_message = ChatMessage(role=ChatRole.USER, content=user_content)
        return (
            ChatRequest(
                messages=[system_message, user_message],
                options=self._options.model_copy(),
            ),
            selection.sources,
        )
