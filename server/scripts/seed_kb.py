from app.schemas.kb import KnowledgeDocumentIngestRequest
from app.services.ingestion_service import IngestionService


def main() -> None:
    service = IngestionService()
    docs = [
        KnowledgeDocumentIngestRequest(
            title="OBD-II PID basics",
            topic="obd",
            pid_tags=["RPM", "COOLANT", "MAF", "MAP"],
            raw_text="OBD-II PIDs describe live engine and vehicle measurements such as RPM, coolant temperature, MAF, MAP, throttle position, and fuel trims.",
        ),
        KnowledgeDocumentIngestRequest(
            title="Fuel trim diagnostics",
            topic="fuel_trim",
            pid_tags=["STFT", "LTFT"],
            raw_text="Positive fuel trims can indicate a lean condition, vacuum leaks, low fuel pressure, or unmetered air. Negative fuel trims can indicate rich operation or leaking injectors.",
        ),
        KnowledgeDocumentIngestRequest(
            title="Coolant overheating checks",
            topic="coolant",
            pid_tags=["COOLANT"],
            raw_text="High coolant temperature may be caused by thermostat failure, cooling fan issues, low coolant, restricted radiator flow, or water pump problems.",
        ),
    ]
    for doc in docs:
        service.ingest_document(doc)
    print("Seeded knowledge base.")


if __name__ == "__main__":
    main()
