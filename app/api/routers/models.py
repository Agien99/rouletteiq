from app.api.auth_guard import legacy_roulette_gate
from fastapi import APIRouter, Depends

from app.api.reporting import (
    APIReportingService,
)
from app.api.schemas import (
    ModelsResponse,
)


router = APIRouter(
    dependencies=[Depends(legacy_roulette_gate)],
    prefix="/models",
    tags=["Models"],
)


@router.get(
    "",
    response_model=ModelsResponse,
)
def get_models():
    return (
        APIReportingService
        .get_models()
    )