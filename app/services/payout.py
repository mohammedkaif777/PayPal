from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.claim import Claim
from app.models.payout import Payout, PayoutAttempt
from app.models.settlement import Settlement, SettlementLine
from app.services.audit import AuditService
from app.services.payment import PaymentAdapter, PayoutLineItem, get_payment_adapter
from app.services.settlement import compute_authorization_hash


class PayoutService:
    @staticmethod
    def execute_payout(
        db: Session,
        *,
        settlement_id: int,
        authorization_nonce: str,
        idempotency_key: str,
        actor: str,
        adapter: PaymentAdapter | None = None,
    ) -> tuple[Payout, list[PayoutAttempt]]:
        settlement = db.get(Settlement, settlement_id)
        if settlement is None:
            raise AppError(
                f"Settlement {settlement_id} not found",
                code="not_found",
                status_code=404,
            )

        existing_by_settlement = db.scalar(
            select(Payout).where(Payout.settlement_id == settlement_id)
        )
        if existing_by_settlement is not None:
            if existing_by_settlement.idempotency_key == idempotency_key:
                attempts = list(
                    db.scalars(
                        select(PayoutAttempt)
                        .where(PayoutAttempt.payout_id == existing_by_settlement.id)
                        .order_by(PayoutAttempt.attempt_number.asc())
                    ).all()
                )
                return existing_by_settlement, attempts
            raise AppError(
                f"Payout already exists for settlement {settlement_id}",
                code="duplicate_payout",
                status_code=409,
                details={"payout_id": existing_by_settlement.id},
            )

        existing_by_idem = db.scalar(
            select(Payout).where(Payout.idempotency_key == idempotency_key)
        )
        if existing_by_idem is not None:
            raise AppError(
                "Payout idempotency_key already used for another settlement",
                code="idempotency_conflict",
                status_code=409,
            )

        if settlement.nonce_used:
            raise AppError(
                "Settlement authorization nonce has already been consumed",
                code="nonce_already_used",
                status_code=409,
            )

        claim = db.get(Claim, settlement.claim_id)
        if claim is None or claim.status not in {"SETTLED", "PAYOUT_FAILED"}:
            raise AppError(
                "Claim is not in an authorized settleable state",
                code="invalid_state",
                status_code=409,
            )

        expected_hash = compute_authorization_hash(
            nonce=authorization_nonce,
            settlement_id=settlement.id,
            total_amount=Decimal(settlement.total_amount),
            currency=settlement.currency,
            decision_hash=claim.decision_hash or "",
        )
        if (
            authorization_nonce != settlement.authorization_nonce
            or expected_hash != settlement.authorization_hash
        ):
            raise AppError(
                "Invalid settlement authorization nonce",
                code="unauthorized_settlement",
                status_code=403,
            )

        # Consume single-use nonce before invoking payment adapter
        settlement.nonce_used = True
        claim.status = "PAYOUT_PENDING"

        payment_adapter = adapter or get_payment_adapter()
        lines = list(
            db.scalars(
                select(SettlementLine)
                .where(SettlementLine.settlement_id == settlement.id)
                .order_by(SettlementLine.id.asc())
            ).all()
        )
        line_items = [
            PayoutLineItem(
                role=line.role,
                recipient_email=line.recipient_email,
                amount=Decimal(line.amount).quantize(Decimal("0.01")),
            )
            for line in lines
        ]

        payout = Payout(
            settlement_id=settlement.id,
            idempotency_key=idempotency_key,
            provider="mock",
            status="SENT",
            amount=Decimal(settlement.total_amount).quantize(Decimal("0.01")),
            currency=settlement.currency,
            attempts=1,
        )
        db.add(payout)
        db.flush()

        result = payment_adapter.pay(
            settlement_id=settlement.id,
            currency=settlement.currency,
            lines=line_items,
            idempotency_key=idempotency_key,
        )
        payout.provider = result.provider
        payout.external_id = result.external_id
        payout.status = "SUCCEEDED" if result.success else "FAILED"
        claim.status = "PAID" if result.success else "PAYOUT_FAILED"

        attempt = PayoutAttempt(
            payout_id=payout.id,
            attempt_number=1,
            request_summary=result.request_summary,
            response_summary=result.response_summary,
            success=result.success,
        )
        db.add(attempt)
        db.flush()

        AuditService.record(
            db,
            actor=actor,
            action="execute_payout",
            entity_type="payout",
            entity_id=str(payout.id),
            after={
                "settlement_id": settlement.id,
                "status": payout.status,
                "external_id": payout.external_id,
                "attempts": payout.attempts,
            },
        )
        return payout, [attempt]

    @staticmethod
    def retry_payout(
        db: Session,
        payout_id: int,
        *,
        actor: str,
        adapter: PaymentAdapter | None = None,
    ) -> tuple[Payout, list[PayoutAttempt]]:
        payout = db.get(Payout, payout_id)
        if payout is None:
            raise AppError(
                f"Payout {payout_id} not found",
                code="not_found",
                status_code=404,
            )
        if payout.status != "FAILED":
            raise AppError(
                f"Only FAILED payouts can be retried (current status: {payout.status})",
                code="invalid_state",
                status_code=409,
            )

        settlement = db.get(Settlement, payout.settlement_id)
        if settlement is None:
            raise AppError("Settlement missing", code="not_found", status_code=404)
        claim = db.get(Claim, settlement.claim_id)
        if claim is None:
            raise AppError("Claim missing", code="not_found", status_code=404)

        lines = list(
            db.scalars(
                select(SettlementLine)
                .where(SettlementLine.settlement_id == settlement.id)
                .order_by(SettlementLine.id.asc())
            ).all()
        )
        line_items = [
            PayoutLineItem(
                role=line.role,
                recipient_email=line.recipient_email,
                amount=Decimal(line.amount).quantize(Decimal("0.01")),
            )
            for line in lines
        ]

        before_status = payout.status
        payout.status = "RETRYING"
        payout.attempts += 1
        db.flush()

        payout.status = "SENT"
        payment_adapter = adapter or get_payment_adapter()
        result = payment_adapter.pay(
            settlement_id=settlement.id,
            currency=settlement.currency,
            lines=line_items,
            idempotency_key=payout.idempotency_key,  # Reuse exact same idempotency key
        )
        payout.provider = result.provider
        payout.external_id = result.external_id
        payout.status = "SUCCEEDED" if result.success else "FAILED"
        claim.status = "PAID" if result.success else "PAYOUT_FAILED"

        attempt = PayoutAttempt(
            payout_id=payout.id,
            attempt_number=payout.attempts,
            request_summary=result.request_summary,
            response_summary=result.response_summary,
            success=result.success,
        )
        db.add(attempt)
        db.flush()

        AuditService.record(
            db,
            actor=actor,
            action="retry_payout",
            entity_type="payout",
            entity_id=str(payout.id),
            before={"status": before_status, "attempts": payout.attempts - 1},
            after={
                "status": payout.status,
                "attempts": payout.attempts,
                "external_id": payout.external_id,
            },
        )
        attempts = list(
            db.scalars(
                select(PayoutAttempt)
                .where(PayoutAttempt.payout_id == payout.id)
                .order_by(PayoutAttempt.attempt_number.asc())
            ).all()
        )
        return payout, attempts

    @staticmethod
    def get(db: Session, payout_id: int) -> tuple[Payout, list[PayoutAttempt]]:
        payout = db.get(Payout, payout_id)
        if payout is None:
            raise AppError(
                f"Payout {payout_id} not found",
                code="not_found",
                status_code=404,
            )
        attempts = list(
            db.scalars(
                select(PayoutAttempt)
                .where(PayoutAttempt.payout_id == payout.id)
                .order_by(PayoutAttempt.attempt_number.asc())
            ).all()
        )
        return payout, attempts

    @staticmethod
    def list_all(db: Session) -> list[Payout]:
        return list(db.scalars(select(Payout).order_by(Payout.id.desc())).all())

