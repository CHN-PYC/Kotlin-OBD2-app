from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.kb import router as kb_router
from app.api.qa import router as qa_router
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(kb_router)
app.include_router(qa_router)
