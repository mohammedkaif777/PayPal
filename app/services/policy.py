from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.policy import Policy
from app.models.shipment import Shipment
from app.schemas.policy import PolicyCreate
from app.services.audit import AuditService

ALLOWED_POLICY_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"ACTIVE", "CANCELLED"},
    "ACTIVE": {"TRIGGERED", "EXPIRED", "CANCELLED"},
    "TRIGGERED": {"SETTLED", "EXPIRED"},
    "SETTLED": set(),
    "EXPIRED": set(),
    "CANCELLED": set(),
}


class PolicyService:
    @staticmethod
    def create(db: Session, data: PolicyCreate, *, actor: str) -> Policy:
        existing = db.scalar(
            select(Policy).where(Policy.policy_number == data.policy_number)
        )
        if existing is not None:
            raise AppError(
                f"Policy '{data.policy_number}' already exists",
                code="conflict",
                status_code=409,
            )

        shipment = db.get(Shipment, data.shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {data.shipment_id} not found",
                code="not_found",
                status_code=404,
            )
        if shipment.status == "CANCELLED":
            raise AppError(
                "Cannot create policy for a cancelled shipment",
                code="invalid_state",
                status_code=409,
            )

        policy = Policy(
            policy_number=data.policy_number,
            shipment_id=data.shipment_id,
            coverage_amount=data.coverage_amount,
            premium_amount=data.premium_amount,
            currency=data.currency,
            temp_min_c=data.temp_min_c,
            temp_max_c=data.temp_max_c,
            humidity_max_pct=data.humidity_max_pct,
            delay_hours_max=data.delay_hours_max,
            geofence_max_km=data.geofence_max_km,
            coverage_start=data.coverage_start,
            coverage_end=data.coverage_end,
            supplier_split_pct=data.supplier_split_pct,
            logistics_split_pct=data.logistics_split_pct,
            version=data.version,
            status="DRAFT",
        )
        db.add(policy)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="create",
            entity_type="policy",
            entity_id=str(policy.id),
            after={
                "policy_number": policy.policy_number,
                "shipment_id": policy.shipment_id,
                "coverage_amount": str(policy.coverage_amount),
                "status": policy.status,
            },
        )
        return policy

    @staticmethod
    def get(db: Session, policy_id: int) -> Policy:
        policy = db.get(Policy, policy_id)
        if policy is None:
            raise AppError(
                f"Policy {policy_id} not found",
                code="not_found",
                status_code=404,
            )
        return policy

    @staticmethod
    def list_all(
        db: Session, *, shipment_id: int | None = None, status: str | None = None
    ) -> list[Policy]:
        stmt = select(Policy).order_by(Policy.id.desc())
        if shipment_id is not None:
            stmt = stmt.where(Policy.shipment_id == shipment_id)
        if status is not None:
            stmt = stmt.where(Policy.status == status)
        return list(db.scalars(stmt).all())

    @staticmethod
    def transition(
        db: Session, policy_id: int, target_status: str, *, actor: str
    ) -> Policy:
        policy = PolicyService.get(db, policy_id)
        allowed = ALLOWED_POLICY_TRANSITIONS.get(policy.status, set())
        if target_status not in allowed:
            raise AppError(
                f"Invalid policy transition from {policy.status} to {target_status}",
                code="invalid_transition",
                status_code=409,
                details={
                    "current_status": policy.status,
                    "requested_status": target_status,
                    "allowed": sorted(allowed),
                },
            )
        before_status = policy.status
        policy.status = target_status
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="transition",
            entity_type="policy",
            entity_id=str(policy.id),
            before={"status": before_status},
            after={"status": policy.status},
        )
        return policy
