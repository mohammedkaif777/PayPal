from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.fraud import (
    FraudEvaluateRequest,
    FraudEvaluateResponse,
    FraudSignalResponse,
    VerificationResultResponse,
)
from app.services.fraud import FraudEngine
from app.services.verification import VerificationService

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.post("/evaluate", response_model=FraudEvaluateResponse)
def evaluate_fraud(
    payload: FraudEvaluateRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer")),
) -> FraudEvaluateResponse:
    verifications, signals = FraudEngine.evaluate(
        db, payload.shipment_id, actor=actor.name
    )
    db.commit()
    return FraudEvaluateResponse(
        shipment_id=payload.shipment_id,
        verifications=[VerificationResultResponse.model_validate(v) for v in verifications],
        signals=[FraudSignalResponse.model_validate(s) for s in signals],
        has_hard_block=any(s.severity == "HARD_BLOCK" for s in signals),
        requires_review=any(s.severity == "REVIEW" for s in signals),
    )


@router.get("/signals/{shipment_id}", response_model=list[FraudSignalResponse])
def list_fraud_signals(
    shipment_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[FraudSignalResponse]:
    rows = FraudEngine.list_signals(db, shipment_id)
    return [FraudSignalResponse.model_validate(r) for r in rows]


@router.get("/verifications/{shipment_id}", response_model=list[VerificationResultResponse])
def list_verifications(
    shipment_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[VerificationResultResponse]:
    rows = VerificationService.list_by_shipment(db, shipment_id)
    return [VerificationResultResponse.model_validate(r) for r in rows]

