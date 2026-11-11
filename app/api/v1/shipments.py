import hashlib
import json

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.shipment import ShipmentCreate, ShipmentResponse, ShipmentStatusUpdate
from app.services.idempotency import IdempotencyService
from app.services.shipment import ShipmentService

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.post("", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_shipment(
    payload: ShipmentCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> ShipmentResponse:
    if idempotency_key:
        req_hash = hashlib.sha256(
            json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode("utf-8")
        ).hexdigest()
        idem = IdempotencyService.begin(
            db, scope="create_shipment", key=idempotency_key, request_hash=req_hash
        )
        if not idem.created:
            response.status_code = idem.record.status_code or status.HTTP_201_CREATED
            return ShipmentResponse.model_validate(idem.record.response_json)

        shipment = ShipmentService.create(db, payload, actor=actor.name)
        db.flush()
        db.refresh(shipment)
        resp_obj = ShipmentResponse.model_validate(shipment)
        IdempotencyService.complete(
            db,
            idem.record,
            status_code=status.HTTP_201_CREATED,
            response=resp_obj.model_dump(mode="json"),
        )
        db.commit()
        return resp_obj

    shipment = ShipmentService.create(db, payload, actor=actor.name)
    db.commit()
    db.refresh(shipment)
    return ShipmentResponse.model_validate(shipment)


@router.get("", response_model=list[ShipmentResponse])
def list_shipments(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[ShipmentResponse]:
    rows = ShipmentService.list_all(db, status=status_filter, limit=limit)
    return [ShipmentResponse.model_validate(row) for row in rows]


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> ShipmentResponse:
    return ShipmentResponse.model_validate(ShipmentService.get(db, shipment_id))


@router.post("/{shipment_id}/transition", response_model=ShipmentResponse)
def transition_shipment(
    shipment_id: int,
    payload: ShipmentStatusUpdate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> ShipmentResponse:
    shipment = ShipmentService.transition(db, shipment_id, payload, actor=actor.name)
    db.commit()
    db.refresh(shipment)
    return ShipmentResponse.model_validate(shipment)
