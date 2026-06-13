from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.common import RetrievedSource


class LlmService:
    def __init__(self) -> None:
        self.base_url = settings.llm_base_url.strip()
        self.api_key = settings.llm_api_key.strip()
        self.model = settings.llm_model.strip()
        self.timeout_seconds = 60.0

    def answer_question(
        self,
        *,
        question: str,
        vehicle_context: dict,
        rule_summary: dict | None,
        sources: list[RetrievedSource],
        rewritten_query: str,
    ) -> dict[str, Any]:
        self._validate_config()
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            question=question,
            vehicle_context=vehicle_context,
            rule_summary=rule_summary,
            sources=sources,
            rewritten_query=rewritten_query,
        )
        response_text, raw_json = self._call_chat_completion(system_prompt, user_prompt)
        return self._parse_response(response_text, raw_json, sources)

    def _validate_config(self) -> None:
        if not self.base_url:
            raise ValueError("LLM_BASE_URL is missing")
        if not self.api_key:
            raise ValueError("LLM_API_KEY is missing")
        if not self.model:
            raise ValueError("LLM_MODEL is missing")

    def _build_system_prompt(self) -> str:
        return (
            "You are an automotive diagnostic Q&A assistant. "
            "Use the provided vehicle context, rule summary, and retrieved knowledge snippets. "
            "Return ONLY valid JSON with keys: severity, answer, findings, recommendations. "
            "findings and recommendations must be arrays of short strings. "
            "Be careful, evidence-based, and explicit about uncertainty."
        )

    def _build_user_prompt(
        self,
        *,
        question: str,
        vehicle_context: dict,
        rule_summary: dict | None,
        sources: list[RetrievedSource],
        rewritten_query: str,
    ) -> str:
        source_lines = []
        for index, source in enumerate(sources, start=1):
            source_lines.append(
                f"[{index}] {source.title} | topic={source.topic or 'unknown'} | url={source.source_url}\n{source.text}"
            )
        source_block = "\n\n".join(source_lines) if source_lines else "No retrieved sources."

        return (
            f"User question:\n{question}\n\n"
            f"Rewritten retrieval query:\n{rewritten_query}\n\n"
            f"Vehicle context JSON:\n{json.dumps(vehicle_context, ensure_ascii=False, indent=2)}\n\n"
            f"Rule summary JSON:\n{json.dumps(rule_summary or {}, ensure_ascii=False, indent=2)}\n\n"
            f"Retrieved sources:\n{source_block}\n\n"
            "Answer the question using only supported evidence."
        )

    def _call_chat_completion(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            raw_json = response.text

        try:
            body = json.loads(raw_json)
            choices = body.get("choices") or []
            first = choices[0] if choices else {}
            message = first.get("message") or {}
            content = message.get("content") or first.get("text") or raw_json
            if isinstance(content, list):
                content = "\n".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            return str(content), raw_json
        except Exception:
            return raw_json, raw_json

    def _parse_response(self, response_text: str, raw_json: str, sources: list[RetrievedSource]) -> dict[str, Any]:
        normalized = (
            response_text.replace("```json", "")
            .replace("```JSON", "")
            .replace("```", "")
            .strip()
        )
        json_candidate = self._extract_first_json_object(normalized) or normalized

        try:
            parsed = json.loads(json_candidate)
            answer = str(parsed.get("answer") or normalized[:1200])
            severity = str(parsed.get("severity") or "NOTICE")
            findings = self._normalize_list(parsed.get("findings"))
            recommendations = self._normalize_list(parsed.get("recommendations"))
            if not findings:
                findings = [f"Retrieved {len(sources)} source chunks for grounding."]
            return {
                "answer": answer,
                "severity": severity,
                "findings": findings,
                "recommendations": recommendations,
                "raw": raw_json,
            }
        except Exception:
            return {
                "answer": normalized[:1200],
                "severity": "NOTICE",
                "findings": [
                    "Model output could not be parsed as structured JSON.",
                    f"Retrieved {len(sources)} source chunks for grounding.",
                ],
                "recommendations": [
                    "Check the backend LLM prompt/formatting.",
                ],
                "raw": raw_json,
            }

    def _normalize_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _extract_first_json_object(self, text: str) -> str | None:
        start = text.find("{")
        if start < 0:
            return None
        depth = 0
        for index in range(start, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        return None
