from app.api.auth_guard import legacy_roulette_gate
from uuid import UUID

from fastapi import (
    Depends,
    APIRouter,
    status,
)

from app.api.errors import APIError
from app.api.schemas import (
    AddSpinRequest,
    InitialSpinsRequest,
    PredictionRequest,
    PredictionResponse,
    SessionResponse,
    SessionStatisticsResponse,
    SpinResponse,
    StoredPredictionResponse,    
    ComparisonResponse,
    EvaluationResponse,
    MLPerformanceResponse,
)
from app.api.services import (
    APIEvaluationService,
    APIPredictionService,
    APIStatisticsService,
)
from app.session import RouletteSession
from app.session_repository import (
    SessionRepository,
)
from app.session_storage_service import (
    SessionStorageService,
)
from app.spin_repository import (
    SpinRepository,
)

from app.api.reporting import (
    APIReportingService,
)

router = APIRouter(
    dependencies=[Depends(legacy_roulette_gate)],
    prefix="/sessions",
    tags=["Sessions"],
)


def load_required_session(
    session_id: UUID,
) -> RouletteSession:
    session = (
        SessionStorageService.load_session(
            str(session_id)
        )
    )

    if session is None:
        raise APIError(
            status_code=404,
            message="Session not found.",
        )

    return session


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session():
    session = RouletteSession()

    return SessionRepository.create_session(
        session
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
)
def get_session(
    session_id: UUID,
):
    session = SessionRepository.get_session(
        str(session_id)
    )

    if session is None:
        raise APIError(
            status_code=404,
            message="Session not found.",
        )

    return session


@router.post(
    "/{session_id}/initial-spins",
    response_model=SessionResponse,
)
def add_initial_spins(
    session_id: UUID,
    request: InitialSpinsRequest,
):
    session = load_required_session(
        session_id
    )

    if session.status != "NEW":
        raise APIError(
            status_code=409,
            message=(
                "Initial spins have already "
                "been submitted for this session."
            ),
        )

    try:
        session.start(
            request.spins
        )

    except ValueError as error:
        raise APIError(
            status_code=400,
            message=str(error),
        ) from error

    SessionRepository.update_session(
        session
    )

    for spin_index, number in enumerate(
        request.spins,
        start=1,
    ):
        SpinRepository.create_spin(
            session_id=session.session_id,
            spin_index=spin_index,
            number=number,
            spin_type="INITIAL",
        )

    stored_session = (
        SessionRepository.get_session(
            session.session_id
        )
    )

    if stored_session is None:
        raise APIError(
            status_code=500,
            message=(
                "Session could not be "
                "reloaded after update."
            ),
        )

    return stored_session


@router.post(
    "/{session_id}/spins",
    response_model=SpinResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_spin(
    session_id: UUID,
    request: AddSpinRequest,
):
    session = load_required_session(
        session_id
    )

    if session.status != "ACTIVE":
        raise APIError(
            status_code=409,
            message=(
                "Spins can only be added "
                "to an active session."
            ),
        )

    spin_index = len(
        session.spins
    ) + 1

    try:
        session.add_spin(
            request.number
        )

    except ValueError as error:
        raise APIError(
            status_code=400,
            message=str(error),
        ) from error

    stored_spin = (
        SpinRepository.create_spin(
            session_id=session.session_id,
            spin_index=spin_index,
            number=request.number,
            spin_type="OBSERVED",
        )
    )

    SessionRepository.update_session(
        session
    )

    APIEvaluationService\
        .evaluate_pending_for_spin(
            session_id=(
                session.session_id
            ),
            actual_spin_id=str(
                stored_spin[
                    "spin_id"
                ]
            ),
            spin_index=spin_index,
            actual_number=request.number,
        )

    return stored_spin


@router.get(
    "/{session_id}/spins",
    response_model=list[SpinResponse],
)
def get_session_spins(
    session_id: UUID,
):
    load_required_session(
        session_id
    )

    return (
        SpinRepository.get_session_spins(
            str(session_id)
        )
    )


@router.get(
    "/{session_id}/stats",
    response_model=SessionStatisticsResponse,
)
def get_session_statistics(
    session_id: UUID,
):
    session = load_required_session(
        session_id
    )

    statistics = (
        APIStatisticsService
        .build_statistics(session)
    )

    return {
        "session_id":
            session.session_id,
        "spin_count":
            len(session.spins),
        "statistics":
            statistics,
    }


@router.post(
    "/{session_id}/predictions",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_prediction(
    session_id: UUID,
    request: PredictionRequest,
):
    session = load_required_session(
        session_id
    )

    try:
        return (
            APIPredictionService.generate(
                session=session,
                strategy=request.strategy,
                recent_window=(
                    request.recent_window
                ),
            )
        )

    except ValueError as error:
        raise APIError(
            status_code=400,
            message=str(error),
        ) from error


@router.get(
    "/{session_id}/predictions/latest",
    response_model=StoredPredictionResponse,
)
def get_latest_prediction(
    session_id: UUID,
):
    load_required_session(
        session_id
    )

    prediction = (
        APIPredictionService.get_latest(
            str(session_id)
        )
    )

    if prediction is None:
        raise APIError(
            status_code=404,
            message=(
                "No predictions found "
                "for this session."
            ),
        )

    return prediction

@router.get(
    "/{session_id}/evaluation",
    response_model=EvaluationResponse,
)
def get_session_evaluation(
    session_id: UUID,
):
    load_required_session(
        session_id
    )

    return (
        APIReportingService
        .get_session_evaluations(
            str(session_id)
        )
    )

@router.get(
    "/{session_id}/comparison",
    response_model=ComparisonResponse,
)
def get_strategy_comparison(
    session_id: UUID,
):
    load_required_session(
        session_id
    )

    return (
        APIReportingService
        .get_strategy_comparison(
            str(session_id)
        )
    )

@router.get(
    "/{session_id}/ml-performance",
    response_model=MLPerformanceResponse,
)
def get_ml_performance(
    session_id: UUID,
):
    load_required_session(
        session_id
    )

    performance = (
        APIReportingService
        .get_ml_performance()
    )

    return {
        "session_id":
            session_id,
        **performance,
    }

@router.post(
    "/{session_id}/end",
    response_model=SessionResponse,
)
def end_session(
    session_id: UUID,
):
    session = load_required_session(
        session_id
    )

    try:
        session.end()

    except ValueError as error:
        raise APIError(
            status_code=409,
            message=str(error),
        ) from error

    SessionRepository.update_session(
        session
    )

    stored_session = (
        SessionRepository.get_session(
            session.session_id
        )
    )

    if stored_session is None:
        raise APIError(
            status_code=500,
            message=(
                "Session could not be "
                "reloaded after ending."
            ),
        )

    return stored_session

@router.get(
    "",
    response_model=list[SessionResponse],
)
def get_historical_sessions():
    return (
        SessionRepository
        .get_all_sessions()
    )