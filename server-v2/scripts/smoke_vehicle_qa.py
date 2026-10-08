"""Run the complete API with real embedding, Qdrant, and configured chat provider."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import httpx2
from fastapi.testclient import TestClient

from app.core.config import ModelProvider, Settings
from app.main import create_app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["configured", "ollama"], default="configured")
    parser.add_argument("--model", default="qwen3:4b", help="Local Ollama chat model")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    if args.provider == "ollama":
        settings = Settings(
            model_provider=ModelProvider.OLLAMA,
            ollama_chat_model=args.model,
            model_timeout_seconds=args.timeout,
            model_max_attempts=1,
        )
    else:
        settings = Settings(
            model_timeout_seconds=args.timeout,
            model_max_attempts=1,
        )
    selected_model = (
        settings.ollama_chat_model
        if settings.model_provider.value == "ollama"
        else settings.llm_model
    )
    print(
        json.dumps(
            {
                "base_url": str(settings.ollama_base_url),
                "provider": settings.model_provider.value,
                "model": selected_model,
                "timeout_seconds": settings.model_timeout_seconds,
                "attempts": settings.model_max_attempts,
            },
            ensure_ascii=False,
        )
    )
    # LEARNING: 配置对象可能包含密钥，只打印明确选择的非敏感字段。
    if settings.model_provider.value == "ollama":
        try:
            with httpx2.Client(timeout=5, trust_env=False) as client:
                response = client.get(f"{str(settings.ollama_base_url).rstrip('/')}/api/tags")
                response.raise_for_status()
                names = [item["name"] for item in response.json()["models"]]
            print(json.dumps({"available_models": names}, ensure_ascii=False))
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as exc:
            print(f"Ollama preflight failed: {type(exc).__name__}")
            print("Continuing to verify the API fallback path.")

    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/vehicle_qa_request.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    # Use a question covered by the bundled knowledge document so this verifies the
    # accepted-evidence branch rather than merely proving that fallback returns 200.
    payload["question"] = "空气流量计异常时应该按什么步骤检查？"
    started = perf_counter()
    # LEARNING: TestClient 只替代入站网络；此处没有 MockTransport，出站是真实 Ollama。
    # Local diagnostic bypasses environment proxies so loopback traffic stays local.
    with TestClient(
        create_app(
            settings=settings,
            client_factory=lambda: httpx2.AsyncClient(trust_env=False),
        )
    ) as client:
        headers = {}
        if settings.api_key is not None:
            headers["Authorization"] = f"Bearer {settings.api_key.get_secret_value()}"
        response = client.post("/qa/vehicle", json=payload, headers=headers)
    print(f"HTTP {response.status_code}; elapsed={perf_counter() - started:.2f}s")
    response.raise_for_status()
    body = response.json()
    print(json.dumps(body, ensure_ascii=False, indent=2))
    # HTTP 200 的降级响应不能当成真实模型成功。
    return 0 if body["answer_mode"] == "llm_rag" else 2


if __name__ == "__main__":
    raise SystemExit(main())
