import json
import sys
from pathlib import Path
from app.schemas.kb import KnowledgeDocumentIngestRequest
from app.services.ingestion_service import IngestionService


def main(path_arg: str) -> None:
    payload = json.loads(Path(path_arg).read_text(encoding="utf-8"))
    request = KnowledgeDocumentIngestRequest(**payload)
    result = IngestionService().ingest_document(request)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m server.scripts.ingest_docs <payload.json>")
    main(sys.argv[1])
