import math
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.policy import Policy
from app.models.port_delay import PortDelay
from app.models.shipment import Shipment
from app.models.telemetry import TelemetryReading
from app.models.violation import Violation
from app.services.audit import AuditService


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * earth_radius_km * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _ensure_utc(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class MonitoringService:
    @staticmethod
    def _record_violation_if_new(
        db: Session,
        *,
        shipment_id: int,
        policy_id: int,
        trigger_code: str,
        severity: str,
        reading_id: int | None,
        port_delay_id: int | None,
        threshold_value: float,
        actual_value: float,
        explanation: str,
        occurred_at,
    ) -> Violation | None:
        stmt = select(Violation).where(
            Violation.shipment_id == shipment_id,
            Violation.policy_id == policy_id,
            Violation.trigger_code == trigger_code,
        )
        if reading_id is not None:
            stmt = stmt.where(Violation.reading_id == reading_id)
        if port_delay_id is not None:
            stmt = stmt.where(Violation.port_delay_id == port_delay_id)
        if db.scalar(stmt) is not None:
            return None

        violation = Violation(
            shipment_id=shipment_id,
            policy_id=policy_id,
            trigger_code=trigger_code,
            severity=severity,
            reading_id=reading_id,
            port_delay_id=port_delay_id,
            threshold_value=threshold_value,
            actual_value=actual_value,
            explanation=explanation,
            occurred_at=occurred_at,
        )
        db.add(violation)
        db.flush()
        return violation

    @staticmethod
    def evaluate_shipment(
        db: Session,
        shipment_id: int,
        *,
        policy_id: int | None = None,
        actor: str = "system",
    ) -> list[Violation]:
        shipment = db.get(Shipment, shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {shipment_id} not found",
                code="not_found",
                status_code=404,
            )

        if policy_id is not None:
            policies = [db.get(Policy, policy_id)]
            policies = [p for p in policies if p is not None and p.shipment_id == shipment_id]
        else:
            policies = list(
                db.scalars(
                    select(Policy).where(
                        Policy.shipment_id == shipment_id,
                        Policy.status.in_(["ACTIVE", "TRIGGERED"]),
                    )
                ).all()
            )

        if not policies:
            raise AppError(
                f"No active policy found for shipment {shipment_id}",
                code="no_active_policy",
                status_code=400,
            )

        readings = list(
            db.scalars(
                select(TelemetryReading)
                .where(TelemetryReading.shipment_id == shipment_id)
                .order_by(TelemetryReading.recorded_at.asc(), TelemetryReading.id.asc())
            ).all()
        )
        delays = list(
            db.scalars(
                select(PortDelay)
                .where(PortDelay.shipment_id == shipment_id)
                .order_by(PortDelay.reported_at.asc(), PortDelay.id.asc())
            ).all()
        )

        created_violations: list[Violation] = []
        waypoints = shipment.route_waypoints or []

        for policy in policies:
            cov_start = _ensure_utc(policy.coverage_start)
            cov_end = _ensure_utc(policy.coverage_end)

            for reading in readings:
                rec_ts = _ensure_utc(reading.recorded_at)
                if rec_ts < cov_start or rec_ts > cov_end:
                    continue

                if reading.temperature_c > policy.temp_max_c:
                    v = MonitoringService._record_violation_if_new(
                        db,
                        shipment_id=shipment_id,
                        policy_id=policy.id,
                        trigger_code="TEMP_HIGH",
                        severity="BREACH",
                        reading_id=reading.id,
                        port_delay_id=None,
                        threshold_value=policy.temp_max_c,
                        actual_value=reading.temperature_c,
                        explanation=(
                            f"Temperature {reading.temperature_c:.2f}C exceeded max "
                            f"{policy.temp_max_c:.2f}C on device {reading.device_id}"
                        ),
                        occurred_at=rec_ts,
                    )
                    if v is not None:
                        created_violations.append(v)

                if reading.temperature_c < policy.temp_min_c:
                    v = MonitoringService._record_violation_if_new(
                        db,
                        shipment_id=shipment_id,
                        policy_id=policy.id,
                        trigger_code="TEMP_LOW",
                        severity="BREACH",
                        reading_id=reading.id,
                        port_delay_id=None,
                        threshold_value=policy.temp_min_c,
                        actual_value=reading.temperature_c,
                        explanation=(
                            f"Temperature {reading.temperature_c:.2f}C dropped below min "
                            f"{policy.temp_min_c:.2f}C on device {reading.device_id}"
                        ),
                        occurred_at=rec_ts,
                    )
                    if v is not None:
                        created_violations.append(v)

                if reading.humidity_pct > policy.humidity_max_pct:
                    v = MonitoringService._record_violation_if_new(
                        db,
                        shipment_id=shipment_id,
                        policy_id=policy.id,
                        trigger_code="HUMIDITY_HIGH",
                        severity="BREACH",
                        reading_id=reading.id,
                        port_delay_id=None,
                        threshold_value=policy.humidity_max_pct,
                        actual_value=reading.humidity_pct,
                        explanation=(
                            f"Humidity {reading.humidity_pct:.2f}% exceeded max "
                            f"{policy.humidity_max_pct:.2f}% on device {reading.device_id}"
                        ),
                        occurred_at=rec_ts,
                    )
                    if v is not None:
                        created_violations.append(v)

                if waypoints:
                    min_dist_km = min(
                        haversine_km(
                            reading.latitude,
                            reading.longitude,
                            float(wp["latitude"]),
                            float(wp["longitude"]),
                        )
                        for wp in waypoints
                    )
                    if min_dist_km > policy.geofence_max_km:
                        v = MonitoringService._record_violation_if_new(
                            db,
                            shipment_id=shipment_id,
                            policy_id=policy.id,
                            trigger_code="GEOFENCE_BREACH",
                            severity="BREACH",
                            reading_id=reading.id,
                            port_delay_id=None,
                            threshold_value=policy.geofence_max_km,
                            actual_value=round(min_dist_km, 2),
                            explanation=(
                                f"Position ({reading.latitude:.4f}, {reading.longitude:.4f}) is "
                                f"{min_dist_km:.2f} km from nearest route waypoint "
                                f"(max {policy.geofence_max_km:.2f} km)"
                            ),
                            occurred_at=rec_ts,
                        )
                        if v is not None:
                            created_violations.append(v)

            for delay in delays:
                rep_ts = _ensure_utc(delay.reported_at)
                if rep_ts < cov_start or rep_ts > cov_end:
                    continue
                delay_val = float(delay.delay_hours)
                if delay_val > policy.delay_hours_max:
                    v = MonitoringService._record_violation_if_new(
                        db,
                        shipment_id=shipment_id,
                        policy_id=policy.id,
                        trigger_code="PORT_DELAY",
                        severity="BREACH",
                        reading_id=None,
                        port_delay_id=delay.id,
                        threshold_value=policy.delay_hours_max,
                        actual_value=delay_val,
                        explanation=(
                            f"Port delay at {delay.port_name} of {delay_val:.2f}h "
                            f"exceeded max {policy.delay_hours_max:.2f}h"
                        ),
                        occurred_at=rep_ts,
                    )
                    if v is not None:
                        created_violations.append(v)

            if created_violations and policy.status == "ACTIVE":
                policy.status = "TRIGGERED"

        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="evaluate_monitoring",
            entity_type="shipment",
            entity_id=str(shipment_id),
            after={"new_violations": len(created_violations)},
        )
        return list(
            db.scalars(
                select(Violation)
                .where(Violation.shipment_id == shipment_id)
                .order_by(Violation.occurred_at.asc(), Violation.id.asc())
            ).all()
        )

    @staticmethod
    def list_violations(db: Session, shipment_id: int) -> list[Violation]:
        return list(
            db.scalars(
                select(Violation)
                .where(Violation.shipment_id == shipment_id)
                .order_by(Violation.occurred_at.asc(), Violation.id.asc())
            ).all()
        )
