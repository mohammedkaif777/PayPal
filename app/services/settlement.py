import hashlib
from decimal import ROUND_DOWN, Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.claim import Claim
from app.models.party import Party
from app.models.policy import Policy
from app.models.settlement import Settlement, SettlementLine
from app.models.shipment import Shipment
from app.services.audit import AuditService


def allocate_split(
    total_amount: Decimal,
    supplier_pct: Decimal,
    logistics_pct: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Largest-remainder allocation in integer cents so supplier + logistics == total_amount exactly.
    """
    total = Decimal(total_amount).quantize(Decimal("0.01"))
    total_cents = int((total * 100).to_integral_value(rounding=ROUND_DOWN))

    raw_supplier = (Decimal(total_cents) * Decimal(supplier_pct)) / Decimal("100")
    raw_logistics = (Decimal(total_cents) * Decimal(logistics_pct)) / Decimal("100")

    floor_supplier = int(raw_supplier.to_integral_value(rounding=ROUND_DOWN))
    floor_logistics = int(raw_logistics.to_integral_value(rounding=ROUND_DOWN))

    remainder_cents = total_cents - (floor_supplier + floor_logistics)
    rem_supplier = raw_supplier - Decimal(floor_supplier)
    rem_logistics = raw_logistics - Decimal(floor_logistics)

    if remainder_cents > 0:
        # Deterministic tie-breaker: supplier first
        if rem_supplier >= rem_logistics:
            floor_supplier += remainder_cents
        else:
            floor_logistics += remainder_cents

    supplier_amount = (Decimal(floor_supplier) / Decimal("100")).quantize(
        Decimal("0.01")
    )
    logistics_amount = (Decimal(floor_logistics) / Decimal("100")).quantize(
        Decimal("0.01")
    )
    return supplier_amount, logistics_amount


def compute_authorization_hash(
    *,
    nonce: str,
    settlement_id: int,
    total_amount: Decimal,
    currency: str,
    decision_hash: str,
) -> str:
    payload = (
        f"{nonce}:{settlement_id}:{Decimal(total_amount):.2f}:{currency}:{decision_hash}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SettlementService:
    @staticmethod
    def create_settlement(
        db: Session, claim_id: int, *, actor: str
    ) -> tuple[Settlement, list[SettlementLine]]:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise AppError(
                f"Claim {claim_id} not found",
                code="not_found",
                status_code=404,
            )
        if claim.status != "APPROVED":
            raise AppError(
                f"Only APPROVED claims can be settled (current status: {claim.status})",
                code="invalid_state",
                status_code=409,
            )

        existing = db.scalar(
            select(Settlement).where(Settlement.claim_id == claim.id)
        )
        if existing is not None:
            lines = list(
                db.scalars(
                    select(SettlementLine).where(
                        SettlementLine.settlement_id == existing.id
                    )
                ).all()
            )
            return existing, lines

        policy = db.get(Policy, claim.policy_id)
        shipment = db.get(Shipment, claim.shipment_id)
        if policy is None or shipment is None:
            raise AppError("Policy or shipment missing", code="not_found", status_code=404)

        supplier = db.get(Party, shipment.supplier_id)
        logistics = db.get(Party, shipment.logistics_id)
        if supplier is None or logistics is None:
            raise AppError("Shipment parties missing", code="not_found", status_code=404)

        total_amount = Decimal(claim.approved_amount).quantize(Decimal("0.01"))
        supplier_amount, logistics_amount = allocate_split(
            total_amount,
            Decimal(policy.supplier_split_pct),
            Decimal(policy.logistics_split_pct),
        )
        nonce = uuid4().hex

        settlement = Settlement(
            claim_id=claim.id,
            total_amount=total_amount,
            currency=policy.currency,
            supplier_amount=supplier_amount,
            logistics_amount=logistics_amount,
            authorization_nonce=nonce,
            authorization_hash="PENDING",
            nonce_used=False,
        )
        db.add(settlement)
        db.flush()

        settlement.authorization_hash = compute_authorization_hash(
            nonce=nonce,
            settlement_id=settlement.id,
            total_amount=total_amount,
            currency=policy.currency,
            decision_hash=claim.decision_hash or "",
        )

        lines = [
            SettlementLine(
                settlement_id=settlement.id,
                party_id=supplier.id,
                role="supplier",
                recipient_email=supplier.payout_email,
                amount=supplier_amount,
            ),
            SettlementLine(
                settlement_id=settlement.id,
                party_id=logistics.id,
                role="logistics",
                recipient_email=logistics.payout_email,
                amount=logistics_amount,
            ),
        ]
        for line in lines:
            db.add(line)

        claim.status = "SETTLED"
        if policy.status in {"ACTIVE", "TRIGGERED"}:
            policy.status = "SETTLED"
        db.flush()

        AuditService.record(
            db,
            actor=actor,
            action="create_settlement",
            entity_type="settlement",
            entity_id=str(settlement.id),
            after={
                "claim_id": claim.id,
                "total_amount": f"{total_amount:.2f}",
                "supplier_amount": f"{supplier_amount:.2f}",
                "logistics_amount": f"{logistics_amount:.2f}",
            },
        )
        return settlement, lines

    @staticmethod
    def get_by_claim(
        db: Session, claim_id: int
    ) -> tuple[Settlement, list[SettlementLine]]:
        settlement = db.scalar(
            select(Settlement).where(Settlement.claim_id == claim_id)
        )
        if settlement is None:
            raise AppError(
                f"Settlement for claim {claim_id} not found",
                code="not_found",
                status_code=404,
            )
        lines = list(
            db.scalars(
                select(SettlementLine)
                .where(SettlementLine.settlement_id == settlement.id)
                .order_by(SettlementLine.id.asc())
            ).all()
        )
        return settlement, lines

    @staticmethod
    def list_all(db: Session) -> list[Settlement]:
        return list(db.scalars(select(Settlement).order_by(Settlement.id.desc())).all())

    @staticmethod
    def get(db: Session, settlement_id: int) -> tuple[Settlement, list[SettlementLine]]:
        settlement = db.get(Settlement, settlement_id)
        if settlement is None:
            raise AppError(
                f"Settlement {settlement_id} not found",
                code="not_found",
                status_code=404,
            )
        lines = list(
            db.scalars(
                select(SettlementLine)
                .where(SettlementLine.settlement_id == settlement.id)
                .order_by(SettlementLine.id.asc())
            ).all()
        )
        return settlement, lines
