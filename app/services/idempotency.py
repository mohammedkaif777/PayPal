from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.idempotency import IdempotencyKey


@dataclass
class IdempotencyResult:
    record: IdempotencyKey
    created: bool


class IdempotencyService:
    @staticmethod
    def begin(
        db: Session,
        *,
        scope: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyResult:
        existing = db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.scope == scope,
                IdempotencyKey.key == key,
            )
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise AppError(
                    "Idempotency key reused with a different request",
                    code="idempotency_conflict",
                    status_code=409,
                )
            if existing.status_code is None:
                raise AppError(
                    "Request already in progress",
                    code="idempotency_in_progress",
                    status_code=409,
                )
            return IdempotencyResult(record=existing, created=False)

        record = IdempotencyKey(scope=scope, key=key, request_hash=request_hash)
        db.add(record)
        db.flush()
        return IdempotencyResult(record=record, created=True)

    @staticmethod
    def complete(
        db: Session,
        record: IdempotencyKey,
        *,
        status_code: int,
        response: dict[str, Any],
    ) -> None:
        record.status_code = status_code
        record.response_json = response
        db.flush()
