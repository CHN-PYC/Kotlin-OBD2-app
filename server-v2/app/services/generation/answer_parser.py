import json

from pydantic import ValidationError

from app.providers.chat import ChatResult
from app.providers.errors import InvalidModelResponseError
from app.schemas.generation import GeneratedVehicleAnswer


class VehicleAnswerParser:
    def parse(self, result: ChatResult) -> GeneratedVehicleAnswer:
        # LEARNING: HTTP 200 和 finish_reason=stop 都不能替代业务 Schema 校验。
        try:
            payload = json.loads(result.content)
            return GeneratedVehicleAnswer.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise InvalidModelResponseError(
                "Model output is not valid vehicle answer JSON",
                provider=result.provider,
                model=result.model,
            ) from exc  # 保留底层 JSON/Pydantic 异常，便于通过 __cause__ 调试。
