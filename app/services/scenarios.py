from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from PIL import Image
from sqlalchemy.orm import Session

from app.schemas.party import PartyCreate
from app.schemas.policy import PolicyCreate
from app.schemas.shipment import ShipmentCreate, ShipmentStatusUpdate, Waypoint
from app.services.claims import ClaimsEngine
from app.services.evidence import EvidenceService
from app.services.fraud import FraudEngine
from app.services.monitoring import MonitoringService
from app.services.party import PartyService
from app.services.payout import PayoutService
from app.services.pdf_fixture import build_simple_pdf
from app.services.policy import PolicyService
from app.services.settlement import SettlementService
from app.services.shipment import ShipmentService
from app.services.simulator import DeterministicSimulator


def _png_bytes(seed: int = 0) -> bytes:
    image = Image.new("RGB", (128, 96), color=(40, 90, 160))
    for y in range(0, 96, 6):
        for x in range(128):
            image.putpixel((x, y), (220, 220, (40 + seed) % 255))
    for x in range(0, 128, 6):
        for y in range(96):
            image.putpixel((x, y), (20, 40, (200 + seed) % 255))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class ScenarioService:
    @staticmethod
    def run(db: Session, *, scenario: str, seed: int, actor: str) -> dict:
        suffix = uuid4().hex[:8]
        now = datetime.now(timezone.utc)
        departure = now - timedelta(hours=6)
        arrival = now + timedelta(days=8)

        supplier = PartyService.create(
            db,
            PartyCreate(
                name=f"AgriFresh Farms {suffix}",
                role="supplier",
                payout_email=f"supplier-{suffix}@sandbox.example",
            ),
            actor=actor,
        )
        logistics = PartyService.create(
            db,
            PartyCreate(
                name=f"ColdChain Logistics {suffix}",
                role="logistics",
                payout_email=f"logistics-{suffix}@sandbox.example",
            ),
            actor=actor,
        )

        external_ref = f"SHIP-{scenario}-{suffix.upper()}"
        shipment = ShipmentService.create(
            db,
            ShipmentCreate(
                external_ref=external_ref,
                commodity="Fresh Mangoes",
                origin_port="Mumbai",
                destination_port="Rotterdam",
                mode="SEA",
                declared_value=Decimal("25000.00"),
                currency="USD",
                supplier_id=supplier.id,
                logistics_id=logistics.id,
                route_waypoints=[
                    Waypoint(name="Mumbai", latitude=19.0760, longitude=72.8777),
                    Waypoint(name="Aden", latitude=12.7855, longitude=45.0187),
                    Waypoint(name="Rotterdam", latitude=51.9225, longitude=4.4792),
                ],
                departure_time=departure,
                expected_arrival_time=arrival,
            ),
            actor=actor,
        )
        ShipmentService.transition(
            db,
            shipment.id,
            ShipmentStatusUpdate(status="IN_TRANSIT"),
            actor=actor,
        )

        policy = PolicyService.create(
            db,
            PolicyCreate(
                policy_number=f"POL-{scenario}-{suffix.upper()}",
                shipment_id=shipment.id,
                coverage_amount=Decimal("10000.00"),
                premium_amount=Decimal("250.00"),
                currency="USD",
                temp_min_c=1.0,
                temp_max_c=8.0,
                humidity_max_pct=85.0,
                delay_hours_max=48.0,
                geofence_max_km=250.0,
                coverage_start=departure - timedelta(hours=1),
                coverage_end=arrival + timedelta(days=2),
                supplier_split_pct=Decimal("60.00"),
                logistics_split_pct=Decimal("40.00"),
            ),
            actor=actor,
        )
        PolicyService.transition(db, policy.id, "ACTIVE", actor=actor)

        ingested, skipped = DeterministicSimulator.run_for_shipment(
            db,
            shipment_id=shipment.id,
            seed=seed,
            num_readings=12,
            scenario=scenario,
            actor=actor,
        )
        violations = MonitoringService.evaluate_shipment(
            db, shipment.id, policy_id=policy.id, actor=actor
        )

        pdf_bytes = build_simple_pdf(
            [
                f"ShipmentRef: {external_ref}",
                "Shipper: AgriFresh Farms Ltd",
                "Consignee: EuroCold Imports GmbH",
                "Vessel: MV Pacific Breeze",
                "OriginPort: Mumbai",
                "DestinationPort: Rotterdam",
                "Commodity: Fresh Mangoes",
                f"DocumentDate: {departure.date().isoformat()}T00:00:00Z",
                "Quantity: 1200 crates",
                "WeightKg: 14400",
            ]
        )
        bol = EvidenceService.upload(
            db,
            shipment_id=shipment.id,
            doc_type="BILL_OF_LADING",
            filename="bill_of_lading.pdf",
            content=pdf_bytes,
            actor=actor,
        )
        EvidenceService.extract(db, bol.id, actor=actor)
        EvidenceService.upload(
            db,
            shipment_id=shipment.id,
            doc_type="PHOTO",
            filename="container.png",
            content=_png_bytes(seed=seed + (0 if scenario == "A" else 77)),
            actor=actor,
        )

        _verifications, signals = FraudEngine.evaluate(
            db, shipment.id, actor=actor
        )
        hard_block = any(s.severity == "HARD_BLOCK" for s in signals)

        claim = ClaimsEngine.submit(
            db,
            policy_id=policy.id,
            trigger_code="TEMP_HIGH",
            occurrence_key=f"{external_ref}-TEMP_HIGH",
            idempotency_key=f"claim-{scenario}-{suffix}",
            actor=actor,
        )
        claim = ClaimsEngine.evaluate(db, claim.id, actor=actor)

        settlement_id = None
        payout_id = None
        payout_status = None
        if claim.status == "APPROVED":
            settlement, _lines = SettlementService.create_settlement(
                db, claim.id, actor=actor
            )
            settlement_id = settlement.id
            payout, _attempts = PayoutService.execute_payout(
                db,
                settlement_id=settlement.id,
                authorization_nonce=settlement.authorization_nonce,
                idempotency_key=f"payout-{scenario}-{suffix}",
                actor=actor,
            )
            payout_id = payout.id
            payout_status = payout.status

        db.flush()
        return {
            "scenario": scenario,
            "seed": seed,
            "shipment_id": shipment.id,
            "policy_id": policy.id,
            "claim_id": claim.id,
            "settlement_id": settlement_id,
            "payout_id": payout_id,
            "claim_status": claim.status,
            "payout_status": payout_status,
            "hard_block": hard_block,
            "summary": {
                "external_ref": external_ref,
                "telemetry_ingested": ingested,
                "telemetry_skipped": skipped,
                "violation_count": len(violations),
                "trigger_codes": sorted({v.trigger_code for v in violations}),
                "fraud_rules": [s.rule_code for s in signals],
                "decision_hash": claim.decision_hash,
            },
        }
