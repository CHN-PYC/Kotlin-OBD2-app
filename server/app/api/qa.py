from fastapi import APIRouter
from app.schemas.qa import VehicleQaRequest, VehicleQaResponse
from app.services.rag_service import RagService

router = APIRouter(prefix="/qa", tags=["qa"])
service = RagService()


@router.post("/vehicle", response_model=VehicleQaResponse)
def ask_vehicle_question(request: VehicleQaRequest) -> VehicleQaResponse:
    return service.answer(request)
