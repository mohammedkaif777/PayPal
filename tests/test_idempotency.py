import pytest

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.services.idempotency import IdempotencyService


def test_idempotent_replay_returns_stored_response(client):
    with SessionLocal() as db:
        result = IdempotencyService.begin(
            db, scope="claim", key="k1", request_hash="h1"
        )
        assert result.created is True
        IdempotencyService.complete(
            db, result.record, status_code=201, response={"id": 1}
        )
        db.commit()

    with SessionLocal() as db:
        replay = IdempotencyService.begin(
            db, scope="claim", key="k1", request_hash="h1"
        )
        assert replay.created is False
        assert replay.record.status_code == 201
        assert replay.record.response_json == {"id": 1}


def test_same_key_different_request_is_rejected(client):
    with SessionLocal() as db:
        IdempotencyService.begin(db, scope="claim", key="k2", request_hash="h1")
        with pytest.raises(AppError) as exc:
            IdempotencyService.begin(
                db, scope="claim", key="k2", request_hash="h2"
            )
        assert exc.value.status_code == 409
        assert exc.value.code == "idempotency_conflict"


def test_in_progress_replay_is_rejected(client):
    with SessionLocal() as db:
        IdempotencyService.begin(db, scope="payout", key="p1", request_hash="h1")
        with pytest.raises(AppError) as exc:
            IdempotencyService.begin(
                db, scope="payout", key="p1", request_hash="h1"
            )
        assert exc.value.code == "idempotency_in_progress"
