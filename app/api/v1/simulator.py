from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.telemetry import TelemetryBulkIngestResponse
from app.schemas.violation import SimulationRequest
from app.services.simulator import DeterministicSimulator

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.post(
    "/run",
    response_model=TelemetryBulkIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_simulation(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> TelemetryBulkIngestResponse:
    ingested, skipped = DeterministicSimulator.run_for_shipment(
        db,
        shipment_id=payload.shipment_id,
        seed=payload.seed,
        num_readings=payload.num_readings,
        scenario=payload.scenario,
        device_id=payload.device_id,
        actor=actor.name,
    )
    db.commit()
    return TelemetryBulkIngestResponse(
        shipment_id=payload.shipment_id,
        ingested_count=ingested,
        duplicate_skipped_count=skipped,
    )
