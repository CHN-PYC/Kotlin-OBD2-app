"""Measure real Ollama latency without changing application defaults."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import httpx2
from pydantic import ValidationError

from app.core.config import Settings
from app.providers.chat import ChatMessage, ChatRequest, ChatRole
from app.schemas.generation import GeneratedVehicleAnswer
from app.schemas.qa import VehicleQARequest
from app.services.generation.prompt_builder import VehicleQAPromptBuilder


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["tiny", "vehicle"], default="tiny")
    parser.add_argument("--tokens", type=int, default=16)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--compact", action="store_true", help="Experimental compact output prompt")
    parser.add_argument("--structured", action="store_true", help="Send JSON Schema to Ollama")
    args = parser.parse_args()
    if args.structured and args.case != "vehicle":
        parser.error("--structured requires --case vehicle")
    if args.tokens < 1 or args.timeout <= 0:
        parser.error("tokens and timeout must be positive")
    settings = Settings()
    if args.case == "vehicle":
        path = Path(__file__).resolve().parents[1] / "tests/fixtures/vehicle_qa_request.json"
        request = VehicleQARequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
        chat = VehicleQAPromptBuilder().build(request)
    else:
        chat = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="Reply only OK.")])
    if args.compact:
        if args.case != "vehicle":
            parser.error("--compact requires --case vehicle")
        # LEARNING: 输出约束只改变本次实验，不覆盖应用默认 Prompt。
        original = chat.messages[0]
        compact = original.model_copy(
            update={
                "content": original.content
                + (
                    " Answer in concise Chinese. The answer must be one short sentence. "
                    "Use at most one short finding and two short recommendations. "
                    "Keep the whole JSON under 120 Chinese characters where possible; "
                    "preserve uncertainty and safety-relevant advice. "
                    "Start directly with the JSON object and omit explanations outside it."
                )
            }
        )
        chat = chat.model_copy(update={"messages": [compact, *chat.messages[1:]]})
    # Match the adapter's actual wire protocol, but measure raw timing fields before parsing.
    payload = {
        "model": settings.ollama_chat_model or "qwen3:4b",
        "messages": [message.model_dump(mode="json") for message in chat.messages],
        "think": False,
        "stream": False,
        "options": {"temperature": 0, "num_predict": args.tokens},
    }
    if args.structured:
        # LEARNING: Schema 描述字段规则，model_dump 导出对象数据，两者用途不同。
        payload["format"] = GeneratedVehicleAnswer.model_json_schema()
    started = perf_counter()
    try:
        with httpx2.Client(timeout=args.timeout, trust_env=False) as client:
            response = client.post(
                f"{str(settings.ollama_base_url).rstrip('/')}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx2.HTTPError as exc:
        provider_error = None
        if isinstance(exc, httpx2.HTTPStatusError):
            try:
                provider_error = str(exc.response.json().get("error", ""))[:400]
            except (ValueError, AttributeError):
                pass
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "provider_error": provider_error,
                    "http_status": (
                        exc.response.status_code
                        if isinstance(exc, httpx2.HTTPStatusError)
                        else None
                    ),
                    "elapsed_seconds": round(perf_counter() - started, 3),
                }
            )
        )
        return 2
    fields = {
        key: data.get(key)
        for key in (
            "done_reason",
            "prompt_eval_count",
            "eval_count",
        )
    }
    for key in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration"):
        value = data.get(key)
        fields[key + "_seconds"] = round(value / 1e9, 3) if value is not None else None
    duration = data.get("eval_duration", 0)
    fields["tokens_per_second"] = (
        round(data.get("eval_count", 0) / (duration / 1e9), 2) if duration else None
    )
    content = data.get("message", {}).get("content", "")
    fields["content_characters"] = len(content)
    fields["case"] = args.case
    fields["output_limit"] = args.tokens
    fields["elapsed_seconds"] = round(perf_counter() - started, 3)
    fields["compact_prompt"] = args.compact
    fields["structured_output"] = args.structured
    if args.case == "vehicle":
        # 与业务 Parser 使用相同的 Schema；格式通过不等于事实正确。
        try:
            answer = GeneratedVehicleAnswer.model_validate(json.loads(content))
        except (ValueError, ValidationError):
            fields["schema_valid"] = False
        else:
            fields["schema_valid"] = True
            if data.get("done_reason") == "stop":
                fields["parsed_answer"] = answer.model_dump(mode="json")
        fields["accepted"] = bool(fields["schema_valid"] and data.get("done_reason") == "stop")
    print(json.dumps(fields, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
