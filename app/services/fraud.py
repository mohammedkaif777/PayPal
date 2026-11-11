from datetime import timezone
from decimal import Decimal

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.fraud import FraudSignal
from app.models.shipment import Shipment
from app.models.telemetry import TelemetryReading
from app.models.verification import VerificationResult
from app.services.audit import AuditService
from app.services.monitoring import haversine_km
from app.services.verification import VerificationService

try:
    from sklearn.ensemble import IsolationForest
except ImportError:  # pragma: no cover - optional until owner runs pip install
    IsolationForest = None


def _ensure_utc(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class FraudEngine:
    @staticmethod
    def evaluate(
        db: Session, shipment_id: int, *, actor: str = "system"
    ) -> tuple[list[VerificationResult], list[FraudSignal]]:
        shipment = db.get(Shipment, shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {shipment_id} not found",
                code="not_found",
                status_code=404,
            )

        verifications = VerificationService.cross_verify_evidence(
            db, shipment_id, actor=actor
        )
        db.execute(delete(FraudSignal).where(FraudSignal.shipment_id == shipment_id))

        signals: list[FraudSignal] = []

        for ver in verifications:
            if not ver.passed:
                if ver.check_code == "IMAGE_INTEGRITY" and ver.details.get(
                    "duplicate_document_id"
                ):
                    signals.append(
                        FraudSignal(
                            shipment_id=shipment_id,
                            rule_code="DUPLICATE_EVIDENCE",
                            severity="HARD_BLOCK",
                            score=Decimal("0.95"),
                            explanation=(
                                f"Evidence document {ver.document_id} duplicates image from "
                                f"document {ver.details['duplicate_document_id']}"
                            ),
                            evidence_refs={
                                "document_id": ver.document_id,
                                "verification_id": ver.id,
                            },
                        )
                    )
                elif ver.check_code in {"SHIPMENT_ID_MATCH", "TIMESTAMP_CONSISTENCY"}:
                    signals.append(
                        FraudSignal(
                            shipment_id=shipment_id,
                            rule_code="DOCUMENT_MISMATCH",
                            severity="HARD_BLOCK",
                            score=Decimal("0.95"),
                            explanation=(
                                f"Evidence verification {ver.check_code} failed for "
                                f"document {ver.document_id}: {ver.details}"
                            ),
                            evidence_refs={
                                "document_id": ver.document_id,
                                "check_code": ver.check_code,
                            },
                        )
                    )
                else:
                    signals.append(
                        FraudSignal(
                            shipment_id=shipment_id,
                            rule_code="LOW_QUALITY_IMAGE",
                            severity="REVIEW",
                            score=Decimal("0.55"),
                            explanation=f"Image QC warning on document {ver.document_id}",
                            evidence_refs={"document_id": ver.document_id},
                        )
                    )

        readings = list(
            db.scalars(
                select(TelemetryReading)
                .where(TelemetryReading.shipment_id == shipment_id)
                .order_by(TelemetryReading.recorded_at.asc(), TelemetryReading.id.asc())
            ).all()
        )

        if len(readings) >= 5:
            humidities = np.array([r.humidity_pct for r in readings], dtype=float)
            temps = np.array([r.temperature_c for r in readings], dtype=float)

            if float(np.std(humidities)) == 0.0:
                signals.append(
                    FraudSignal(
                        shipment_id=shipment_id,
                        rule_code="STUCK_SENSOR",
                        severity="HARD_BLOCK",
                        score=Decimal("0.92"),
                        explanation=(
                            f"Humidity sensor flatlined at exactly {humidities[0]:.2f}% "
                            f"across {len(readings)} consecutive readings"
                        ),
                        evidence_refs={"reading_ids": [r.id for r in readings[:10]]},
                    )
                )
            elif float(np.std(temps)) == 0.0:
                signals.append(
                    FraudSignal(
                        shipment_id=shipment_id,
                        rule_code="STUCK_SENSOR",
                        severity="REVIEW",
                        score=Decimal("0.70"),
                        explanation=(
                            f"Temperature sensor flatlined at {temps[0]:.2f}C across "
                            f"{len(readings)} consecutive readings"
                        ),
                        evidence_refs={"reading_ids": [r.id for r in readings[:10]]},
                    )
                )

            # Check consecutive reading deltas (temperature jumps and geofence teleportation)
            for prev, curr in zip(readings, readings[1:]):
                dt_hours = max(
                    (_ensure_utc(curr.recorded_at) - _ensure_utc(prev.recorded_at)).total_seconds()
                    / 3600.0,
                    1e-4,
                )
                temp_delta = abs(curr.temperature_c - prev.temperature_c)
                if dt_hours <= 1.0 and temp_delta > 20.0:
                    signals.append(
                        FraudSignal(
                            shipment_id=shipment_id,
                            rule_code="IMPOSSIBLE_TEMP_DELTA",
                            severity="HARD_BLOCK",
                            score=Decimal("0.96"),
                            explanation=(
                                f"Impossible temperature jump of {temp_delta:.2f}C in "
                                f"{dt_hours * 60:.1f} minutes between readings {prev.id} and {curr.id}"
                            ),
                            evidence_refs={"reading_ids": [prev.id, curr.id]},
                        )
                    )
                    break

            for prev, curr in zip(readings, readings[1:]):
                dt_hours = max(
                    (_ensure_utc(curr.recorded_at) - _ensure_utc(prev.recorded_at)).total_seconds()
                    / 3600.0,
                    1e-4,
                )
                dist_km = haversine_km(
                    prev.latitude, prev.longitude, curr.latitude, curr.longitude
                )
                speed_kmh = dist_km / dt_hours
                max_speed = 950.0 if shipment.mode == "AIR" else 250.0
                if speed_kmh > max_speed:
                    signals.append(
                        FraudSignal(
                            shipment_id=shipment_id,
                            rule_code="GEOFENCE_JUMP",
                            severity="HARD_BLOCK",
                            score=Decimal("0.94"),
                            explanation=(
                                f"Impossible coordinate jump of {dist_km:.1f} km in "
                                f"{dt_hours * 60:.1f} min ({speed_kmh:.0f} km/h > {max_speed:.0f} km/h)"
                            ),
                            evidence_refs={"reading_ids": [prev.id, curr.id]},
                        )
                    )
                    break

            # Statistical anomaly detection (deterministic IsolationForest + z-score)
            temp_std = float(np.std(temps))
            if temp_std > 0:
                z_scores = np.abs((temps - float(np.mean(temps))) / temp_std)
                max_z = float(np.max(z_scores))
                iso_outlier = False
                if IsolationForest is not None and len(readings) >= 8:
                    features = np.column_stack([temps, humidities])
                    clf = IsolationForest(contamination=0.1, random_state=42)
                    preds = clf.fit_predict(features)
                    iso_outlier = bool(np.any(preds == -1)) and max_z > 2.5

                # Genuine parametric heat/cold excursions are expected to look
                # statistically unusual. Record the score as INFO so it does not
                # gate a valid Scenario A payout; hard-block rules still apply.
                if max_z >= 3.0 or iso_outlier:
                    outlier_idx = int(np.argmax(z_scores))
                    outlier_reading = readings[outlier_idx]
                    signals.append(
                        FraudSignal(
                            shipment_id=shipment_id,
                            rule_code="STATISTICAL_OUTLIER",
                            severity="INFO",
                            score=Decimal("0.68"),
                            explanation=(
                                f"Statistical telemetry anomaly on reading {outlier_reading.id}: "
                                f"temp z-score={max_z:.2f}"
                            ),
                            evidence_refs={"reading_ids": [outlier_reading.id]},
                        )
                    )

        for sig in signals:
            db.add(sig)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="evaluate_fraud",
            entity_type="shipment",
            entity_id=str(shipment_id),
            after={
                "signal_count": len(signals),
                "hard_blocks": sum(1 for s in signals if s.severity == "HARD_BLOCK"),
                "reviews": sum(1 for s in signals if s.severity == "REVIEW"),
            },
        )
        return verifications, signals

    @staticmethod
    def list_signals(db: Session, shipment_id: int) -> list[FraudSignal]:
        return list(
            db.scalars(
                select(FraudSignal)
                .where(FraudSignal.shipment_id == shipment_id)
                .order_by(FraudSignal.id.asc())
            ).all()
        )
