import os
from uuid import uuid4

import pytest

from app.database_service import (
    DatabaseService,
)
from app.evaluation import (
    PredictionEvaluationRecord,
)
from app.evaluation_storage_service import (
    EvaluationStorageService,
)
from app.ml.neon_training import (
    NeonTrainingDataService,
)
from app.prediction_item_repository import (
    PredictionItemRepository,
)
from app.prediction_run_repository import (
    PredictionRunRepository,
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


RUN_NEON_INTEGRATION = (
    os.getenv("RUN_NEON_INTEGRATION")
    == "1"
)


pytestmark = pytest.mark.skipif(
    not RUN_NEON_INTEGRATION,
    reason=(
        "Live Neon integration tests "
        "are disabled."
    ),
)


@pytest.fixture(autouse=True)
def integration_session_owner():
    from app.api.auth_guard import _current_user_id

    user_id = str(uuid4())
    email = f"integration-{uuid4().hex}@example.com"

    DatabaseService.execute(
        """
        INSERT INTO public.users (
            user_id, full_name, email,
            role, is_active, email_verified_at
        )
        VALUES (%s, %s, %s, 'user', TRUE, NOW())
        """,
        (user_id, "Integration Test User", email),
    )

    token = _current_user_id.set(user_id)

    try:
        yield
    finally:
        _current_user_id.reset(token)
        DatabaseService.execute(
            "DELETE FROM public.users WHERE user_id = %s",
            (user_id,),
        )


def cleanup_session(
    session_id: str,
) -> None:
    DatabaseService.execute(
        """
        delete from public.sessions
        where session_id = %s
        """,
        (session_id,),
    )

def test_full_neon_session_flow():
    session = RouletteSession()

    initial_spins = [
        17,
        7,
        32,
        14,
        20,
        1,
        9,
        28,
        5,
        31,
    ]

    try:
        # ----------------------------------
        # Create session
        # ----------------------------------

        SessionRepository.create_session(
            session
        )

        session.start(
            initial_spins
        )

        SessionRepository.update_session(
            session
        )

        # ----------------------------------
        # Store initial spins
        # ----------------------------------

        for index, number in enumerate(
            initial_spins,
            start=1,
        ):
            SpinRepository.create_spin(
                session_id=session.session_id,
                spin_index=index,
                number=number,
                spin_type="INITIAL",
            )

        # ----------------------------------
        # Create prediction run for spin 11
        # ----------------------------------

        prediction_run = (
            PredictionRunRepository
            .create_prediction_run(
                session_id=session.session_id,
                strategy_key="v1",
                prediction_for_spin_index=11,
                input_spin_count=10,
                recent_window=10,
            )
        )

        prediction_run_id = str(
            prediction_run[
                "prediction_run_id"
            ]
        )

        # ----------------------------------
        # Store prediction categories
        # ----------------------------------

        items = {
            "DOZENS": [
                {
                    "rank": 1,
                    "dozen": 2,
                    "score": 0.8,
                },
                {
                    "rank": 2,
                    "dozen": 1,
                    "score": 0.6,
                },
            ],
            "COLUMNS": [
                {
                    "rank": 1,
                    "column": 2,
                    "score": 0.7,
                },
                {
                    "rank": 2,
                    "column": 1,
                    "score": 0.5,
                },
            ],
            "STREETS": [
                {
                    "rank": 1,
                    "street": [
                        16,
                        17,
                        18,
                    ],
                    "score": 0.9,
                }
            ],
            "SPLITS": [
                {
                    "rank": 1,
                    "split": [
                        17,
                        20,
                    ],
                    "score": 0.8,
                }
            ],
            "CORNERS": [
                {
                    "rank": 1,
                    "corner": [
                        16,
                        17,
                        19,
                        20,
                    ],
                    "score": 0.7,
                }
            ],
        }

        for category, payload in items.items():
            (
                PredictionItemRepository
                .create_prediction_item(
                    prediction_run_id=(
                        prediction_run_id
                    ),
                    category=category,
                    payload=payload,
                )
            )

        # ----------------------------------
        # Actual next spin occurs
        # ----------------------------------

        actual_number = 17

        session.add_spin(
            actual_number
        )

        actual_spin = (
            SpinRepository.create_spin(
                session_id=session.session_id,
                spin_index=11,
                number=actual_number,
                spin_type="OBSERVED",
            )
        )

        actual_spin_id = str(
            actual_spin["spin_id"]
        )

        # ----------------------------------
        # Evaluation
        # ----------------------------------

        evaluation = (
            PredictionEvaluationRecord(
                actual_number=17,
                evaluated_at=(
                    session.started_at
                ),
                dozen_hit=True,
                column_hit=True,
                street_hit=True,
                split_hit=True,
                corner_hit=True,
            )
        )

        EvaluationStorageService.save_evaluation(
            prediction_run_id=(
                prediction_run_id
            ),
            actual_spin_id=actual_spin_id,
            evaluation=evaluation,
        )

        # ----------------------------------
        # Verify reconstruction
        # ----------------------------------

        reconstructed = (
            SessionStorageService
            .load_session(
                session.session_id
            )
        )

        assert reconstructed is not None

        assert (
            reconstructed.initial_spins
            == initial_spins
        )

        assert reconstructed.spins == (
            initial_spins
            + [actual_number]
        )

        # ----------------------------------
        # Verify evaluation persistence
        # ----------------------------------

        stored_items = (
            PredictionItemRepository
            .get_prediction_items(
                prediction_run_id
            )
        )

        evaluated_items = [
            item
            for item in stored_items
            if item["category"]
            != "NUMBER_PROBABILITIES"
        ]

        assert len(evaluated_items) == 5

        assert all(
            item["is_hit"] is True
            for item in evaluated_items
        )

    finally:
        cleanup_session(
            session.session_id
        )

def test_neon_history_builds_ml_dataset():
    session = RouletteSession()

    spins = [
        1,
        7,
        13,
        22,
        31,
        5,
        18,
        27,
        9,
        34,
        11,
        20,
        3,
        24,
        17,
    ]

    try:
        SessionRepository.create_session(
            session
        )

        session.start(
            spins[:10]
        )

        SessionRepository.update_session(
            session
        )

        for index, number in enumerate(
            spins,
            start=1,
        ):
            spin_type = (
                "INITIAL"
                if index <= 10
                else "OBSERVED"
            )

            SpinRepository.create_spin(
                session_id=session.session_id,
                spin_index=index,
                number=number,
                spin_type=spin_type,
            )

        service = NeonTrainingDataService(
            minimum_history=10,
            recent_window=10,
        )

        dataset = (
            service.build_training_dataset()
        )

        assert len(dataset.X) >= 5
        assert len(dataset.X) == len(
            dataset.y
        )

        assert all(
            0 <= target <= 36
            for target in dataset.y
        )

    finally:
        cleanup_session(
            session.session_id
        )