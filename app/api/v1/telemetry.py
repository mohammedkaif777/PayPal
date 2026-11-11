from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.port_delay import PortDelayCreate, PortDelayResponse
from app.schemas.telemetry import (
    TelemetryBulkIngestRequest,
    TelemetryBulkIngestResponse,
    TelemetryResponse,
)
from app.services.telemetry import PortDelayService, TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post(
    "/ingest",
    response_model=TelemetryBulkIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_telemetry(
    payload: TelemetryBulkIngestRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> TelemetryBulkIngestResponse:
    ingested, skipped = TelemetryService.bulk_ingest(db, payload, actor=actor.name)
    db.commit()
    return TelemetryBulkIngestResponse(
        shipment_id=payload.shipment_id,
        ingested_count=ingested,
        duplicate_skipped_count=skipped,
    )


@router.get("/shipment/{shipment_id}", response_model=list[TelemetryResponse])
def list_telemetry(
    shipment_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[TelemetryResponse]:
    rows = TelemetryService.list_by_shipment(db, shipment_id)
    return [TelemetryResponse.model_validate(r) for r in rows]


@router.post(
    "/port-delays",
    response_model=PortDelayResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_port_delay(
    payload: PortDelayCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PortDelayResponse:
    delay = PortDelayService.create(db, payload, actor=actor.name)
    db.commit()
    db.refresh(delay)
    return PortDelayResponse.model_validate(delay)


@router.get("/port-delays/shipment/{shipment_id}", response_model=list[PortDelayResponse])
def list_port_delays(
    shipment_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[PortDelayResponse]:
    rows = PortDelayService.list_by_shipment(db, shipment_id)
    return [PortDelayResponse.model_validate(r) for r in rows]
