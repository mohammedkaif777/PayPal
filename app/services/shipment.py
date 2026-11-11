from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.shipment import ShipmentCreate, ShipmentStatusUpdate
from app.services.audit import AuditService

ALLOWED_SHIPMENT_TRANSITIONS: dict[str, set[str]] = {
    "REGISTERED": {"IN_TRANSIT", "CANCELLED"},
    "IN_TRANSIT": {"DELIVERED", "CANCELLED"},
    "DELIVERED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
}


class ShipmentService:
    @staticmethod
    def create(db: Session, data: ShipmentCreate, *, actor: str) -> Shipment:
        existing = db.scalar(
            select(Shipment).where(Shipment.external_ref == data.external_ref)
        )
        if existing is not None:
            raise AppError(
                f"Shipment external_ref '{data.external_ref}' already exists",
                code="conflict",
                status_code=409,
            )

        supplier = db.get(Party, data.supplier_id)
        if supplier is None or supplier.role != "supplier":
            raise AppError(
                "Invalid supplier_id: party must exist with role 'supplier'",
                code="invalid_party",
                status_code=400,
            )
        logistics = db.get(Party, data.logistics_id)
        if logistics is None or logistics.role != "logistics":
            raise AppError(
                "Invalid logistics_id: party must exist with role 'logistics'",
                code="invalid_party",
                status_code=400,
            )

        waypoints = (
            [wp.model_dump() for wp in data.route_waypoints]
            if data.route_waypoints is not None
            else None
        )
        shipment = Shipment(
            external_ref=data.external_ref,
            commodity=data.commodity,
            origin_port=data.origin_port,
            destination_port=data.destination_port,
            mode=data.mode,
            declared_value=data.declared_value,
            currency=data.currency,
            supplier_id=data.supplier_id,
            logistics_id=data.logistics_id,
            route_waypoints=waypoints,
            departure_time=data.departure_time,
            expected_arrival_time=data.expected_arrival_time,
            status="REGISTERED",
        )
        db.add(shipment)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="create",
            entity_type="shipment",
            entity_id=str(shipment.id),
            after={
                "external_ref": shipment.external_ref,
                "status": shipment.status,
                "declared_value": str(shipment.declared_value),
            },
        )
        return shipment

    @staticmethod
    def get(db: Session, shipment_id: int) -> Shipment:
        shipment = db.get(Shipment, shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {shipment_id} not found",
                code="not_found",
                status_code=404,
            )
        return shipment

    @staticmethod
    def list_all(
        db: Session, *, status: str | None = None, limit: int = 100
    ) -> list[Shipment]:
        stmt = select(Shipment).order_by(Shipment.id.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(Shipment.status == status)
        return list(db.scalars(stmt).all())

    @staticmethod
    def transition(
        db: Session,
        shipment_id: int,
        update: ShipmentStatusUpdate,
        *,
        actor: str,
    ) -> Shipment:
        shipment = ShipmentService.get(db, shipment_id)
        allowed = ALLOWED_SHIPMENT_TRANSITIONS.get(shipment.status, set())
        if update.status not in allowed:
            raise AppError(
                f"Invalid shipment transition from {shipment.status} to {update.status}",
                code="invalid_transition",
                status_code=409,
                details={
                    "current_status": shipment.status,
                    "requested_status": update.status,
                    "allowed": sorted(allowed),
                },
            )
        before_status = shipment.status
        shipment.status = update.status
        if update.status == "DELIVERED":
            shipment.actual_arrival_time = update.actual_arrival_time or datetime.now(
                timezone.utc
            )
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="transition",
            entity_type="shipment",
            entity_id=str(shipment.id),
            before={"status": before_status},
            after={"status": shipment.status},
        )
        return shipment
