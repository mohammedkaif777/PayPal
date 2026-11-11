from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.violation import MonitoringEvaluateRequest, ViolationResponse
from app.services.monitoring import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/evaluate", response_model=list[ViolationResponse])
def evaluate_monitoring(
    payload: MonitoringEvaluateRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> list[ViolationResponse]:
    violations = MonitoringService.evaluate_shipment(
        db, payload.shipment_id, policy_id=payload.policy_id, actor=actor.name
    )
    db.commit()
    return [ViolationResponse.model_validate(v) for v in violations]


@router.get("/violations/{shipment_id}", response_model=list[ViolationResponse])
def list_violations(
    shipment_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[ViolationResponse]:
    rows = MonitoringService.list_violations(db, shipment_id)
    return [ViolationResponse.model_validate(v) for v in rows]
