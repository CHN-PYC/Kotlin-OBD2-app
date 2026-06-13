from app.core.config import EXPORTS_DIR
from app.core.constants import QA_LOG_FILE
from app.models.qa_log import QaLog
from app.utils.json_utils import append_jsonl, read_jsonl


log_path = EXPORTS_DIR / QA_LOG_FILE


class QaLogRepository:
    def save(self, log: QaLog) -> None:
        append_jsonl(log_path, [log.model_dump()])

    def list_all(self) -> list[QaLog]:
        return [QaLog(**item) for item in read_jsonl(log_path)]
