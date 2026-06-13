from pathlib import Path
from pydantic import BaseModel
import os


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DOCS_DIR = DATA_DIR / "raw_docs"
PROCESSED_DOCS_DIR = DATA_DIR / "processed_docs"
FAISS_DIR = DATA_DIR / "faiss"
EXPORTS_DIR = DATA_DIR / "exports"


class Settings(BaseModel):
    app_name: str = "vehicle-rag-server"
    app_env: str = os.getenv("APP_ENV", "dev")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    top_k_default: int = int(os.getenv("TOP_K_DEFAULT", "5"))


settings = Settings()

for path in [DATA_DIR, RAW_DOCS_DIR, PROCESSED_DOCS_DIR, FAISS_DIR, EXPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)
