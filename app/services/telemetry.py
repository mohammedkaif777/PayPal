from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.port_delay import PortDelay
from app.models.shipment import Shipment
from app.models.telemetry import TelemetryReading
from app.schemas.port_delay import PortDelayCreate
from app.schemas.telemetry import TelemetryBulkIngestRequest
from app.services.audit import AuditService


class TelemetryService:
    @staticmethod
    def bulk_ingest(
        db: Session, payload: TelemetryBulkIngestRequest, *, actor: str
    ) -> tuple[int, int]:
        shipment = db.get(Shipment, payload.shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {payload.shipment_id} not found",
                code="not_found",
                status_code=404,
            )

        sorted_points = sorted(
            payload.readings, key=lambda r: (r.device_id, r.recorded_at)
        )
        seen_in_batch: set[tuple[str, str]] = set()
        ingested = 0
        skipped = 0

        for point in sorted_points:
            ts_key = (point.device_id, point.recorded_at.isoformat())
            if ts_key in seen_in_batch:
                skipped += 1
                continue
            seen_in_batch.add(ts_key)

            existing = db.scalar(
                select(TelemetryReading).where(
                    TelemetryReading.shipment_id == payload.shipment_id,
                    TelemetryReading.device_id == point.device_id,
                    TelemetryReading.recorded_at == point.recorded_at,
                )
            )
            if existing is not None:
                skipped += 1
                continue

            db.add(
                TelemetryReading(
                    shipment_id=payload.shipment_id,
                    device_id=point.device_id,
                    recorded_at=point.recorded_at,
                    temperature_c=point.temperature_c,
                    humidity_pct=point.humidity_pct,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    source=point.source,
                )
            )
            ingested += 1

        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="ingest_telemetry",
            entity_type="shipment",
            entity_id=str(payload.shipment_id),
            after={"ingested": ingested, "duplicate_skipped": skipped},
        )
        return ingested, skipped

    @staticmethod
    def list_by_shipment(db: Session, shipment_id: int) -> list[TelemetryReading]:
        return list(
            db.scalars(
                select(TelemetryReading)
                .where(TelemetryReading.shipment_id == shipment_id)
                .order_by(TelemetryReading.recorded_at.asc(), TelemetryReading.id.asc())
            ).all()
        )


class PortDelayService:
    @staticmethod
    def create(db: Session, payload: PortDelayCreate, *, actor: str) -> PortDelay:
        shipment = db.get(Shipment, payload.shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {payload.shipment_id} not found",
                code="not_found",
                status_code=404,
            )
        delay = PortDelay(
            shipment_id=payload.shipment_id,
            port_name=payload.port_name,
            delay_hours=payload.delay_hours,
            reported_at=payload.reported_at,
            source=payload.source,
        )
        db.add(delay)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="record_port_delay",
            entity_type="port_delay",
            entity_id=str(delay.id),
            after={
                "shipment_id": delay.shipment_id,
                "port_name": delay.port_name,
                "delay_hours": str(delay.delay_hours),
            },
        )
        return delay

    @staticmethod
    def list_by_shipment(db: Session, shipment_id: int) -> list[PortDelay]:
        return list(
            db.scalars(
                select(PortDelay)
                .where(PortDelay.shipment_id == shipment_id)
                .order_by(PortDelay.reported_at.asc(), PortDelay.id.asc())
            ).all()
        )
