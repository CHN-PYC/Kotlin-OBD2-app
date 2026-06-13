from app.services.ingestion_service import IngestionService


def main() -> None:
    IngestionService().rebuild_index()
    print("Rebuilt vector index.")


if __name__ == "__main__":
    main()
