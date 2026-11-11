from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.payout import (
    PayoutAttemptResponse,
    PayoutExecuteRequest,
    PayoutResponse,
)
from app.services.payout import PayoutService

router = APIRouter(prefix="/payouts", tags=["payouts"])


def _to_response(payout, attempts) -> PayoutResponse:
    resp = PayoutResponse.model_validate(payout)
    resp.attempt_history = [PayoutAttemptResponse.model_validate(a) for a in attempts]
    return resp


@router.post("", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
def execute_payout(
    payload: PayoutExecuteRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PayoutResponse:
    payout, attempts = PayoutService.execute_payout(
        db,
        settlement_id=payload.settlement_id,
        authorization_nonce=payload.authorization_nonce,
        idempotency_key=payload.idempotency_key,
        actor=actor.name,
    )
    db.commit()
    db.refresh(payout)
    return _to_response(payout, attempts)


@router.get("", response_model=list[PayoutResponse])
def list_payouts(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[PayoutResponse]:
    payouts = PayoutService.list_all(db)
    results = []
    for p in payouts:
        _, attempts = PayoutService.get(db, p.id)
        results.append(_to_response(p, attempts))
    return results


@router.get("/{payout_id}", response_model=PayoutResponse)
def get_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> PayoutResponse:
    payout, attempts = PayoutService.get(db, payout_id)
    return _to_response(payout, attempts)


@router.post("/{payout_id}/retry", response_model=PayoutResponse)
def retry_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PayoutResponse:
    payout, attempts = PayoutService.retry_payout(db, payout_id, actor=actor.name)
    db.commit()
    db.refresh(payout)
    return _to_response(payout, attempts)

