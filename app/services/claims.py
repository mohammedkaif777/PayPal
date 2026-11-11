import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.claim import Claim
from app.models.fraud import FraudSignal
from app.models.policy import Policy
from app.models.violation import Violation
from app.services.audit import AuditService


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class ClaimDecisionResult:
    status: str
    approved_amount: Decimal
    decision_trace: list[dict[str, Any]]
    input_hash: str
    decision_hash: str


def compute_pure_claim_decision(
    *,
    policy_snapshot: dict[str, Any],
    trigger_code: str,
    occurrence_key: str,
    violations_snapshot: list[dict[str, Any]],
    fraud_snapshot: list[dict[str, Any]],
) -> ClaimDecisionResult:
    """
    Pure deterministic claims evaluation function.
    Identical inputs always produce identical decision_trace, input_hash, and decision_hash.
    """
    canonical_inputs = {
        "policy": policy_snapshot,
        "trigger_code": trigger_code,
        "occurrence_key": occurrence_key,
        "violations": sorted(violations_snapshot, key=lambda v: (v["id"], v["occurred_at"])),
        "fraud_signals": sorted(fraud_snapshot, key=lambda f: (f["id"], f["rule_code"])),
    }
    input_hash = _canonical_hash(canonical_inputs)
    trace: list[dict[str, Any]] = []

    policy_status = policy_snapshot["status"]
    policy_active = policy_status in {"ACTIVE", "TRIGGERED"}
    trace.append(
        {
            "step": "policy_eligibility",
            "passed": policy_active,
            "detail": f"Policy status is {policy_status}",
        }
    )

    cov_start = policy_snapshot["coverage_start"]
    cov_end = policy_snapshot["coverage_end"]
    matching_violations = [
        v
        for v in violations_snapshot
        if v["trigger_code"] == trigger_code and cov_start <= v["occurred_at"] <= cov_end
    ]
    trigger_met = len(matching_violations) > 0
    trace.append(
        {
            "step": "parametric_trigger_check",
            "passed": trigger_met,
            "detail": f"Found {len(matching_violations)} matching violation(s) for {trigger_code} within coverage window",
            "violation_ids": [v["id"] for v in matching_violations],
        }
    )

    hard_blocks = [f for f in fraud_snapshot if f["severity"] == "HARD_BLOCK"]
    reviews = [f for f in fraud_snapshot if f["severity"] == "REVIEW"]
    fraud_clear = len(hard_blocks) == 0 and len(reviews) == 0
    trace.append(
        {
            "step": "fraud_gate",
            "passed": fraud_clear,
            "hard_blocks": [f["rule_code"] for f in hard_blocks],
            "review_flags": [f["rule_code"] for f in reviews],
        }
    )

    coverage_amount = Decimal(str(policy_snapshot["coverage_amount"])).quantize(
        Decimal("0.01")
    )

    if not policy_active or not trigger_met or hard_blocks:
        outcome_status = "REJECTED"
        approved_amount = Decimal("0.00")
    elif reviews:
        outcome_status = "REVIEW_REQUIRED"
        approved_amount = Decimal("0.00")
    else:
        outcome_status = "APPROVED"
        approved_amount = coverage_amount

    trace.append(
        {
            "step": "payout_calculation",
            "outcome": outcome_status,
            "approved_amount": f"{approved_amount:.2f}",
            "currency": policy_snapshot["currency"],
        }
    )

    decision_hash = _canonical_hash(
        {
            "input_hash": input_hash,
            "status": outcome_status,
            "approved_amount": f"{approved_amount:.2f}",
            "decision_trace": trace,
        }
    )
    return ClaimDecisionResult(
        status=outcome_status,
        approved_amount=approved_amount,
        decision_trace=trace,
        input_hash=input_hash,
        decision_hash=decision_hash,
    )


class ClaimsEngine:
    @staticmethod
    def submit(
        db: Session,
        *,
        policy_id: int,
        trigger_code: str,
        occurrence_key: str,
        idempotency_key: str,
        actor: str,
    ) -> Claim:
        policy = db.get(Policy, policy_id)
        if policy is None:
            raise AppError(
                f"Policy {policy_id} not found",
                code="not_found",
                status_code=404,
            )

        dup_occurrence = db.scalar(
            select(Claim).where(
                Claim.policy_id == policy_id,
                Claim.trigger_code == trigger_code,
                Claim.occurrence_key == occurrence_key,
            )
        )
        if dup_occurrence is not None:
            raise AppError(
                "Duplicate claim occurrence for policy, trigger_code, and occurrence_key",
                code="duplicate_occurrence",
                status_code=409,
                details={"existing_claim_id": dup_occurrence.id},
            )

        dup_idem = db.scalar(
            select(Claim).where(Claim.idempotency_key == idempotency_key)
        )
        if dup_idem is not None:
            raise AppError(
                "Claim idempotency_key already used",
                code="idempotency_conflict",
                status_code=409,
                details={"existing_claim_id": dup_idem.id},
            )

        claim = Claim(
            policy_id=policy.id,
            shipment_id=policy.shipment_id,
            trigger_code=trigger_code,
            occurrence_key=occurrence_key,
            claimed_amount=policy.coverage_amount,
            approved_amount=Decimal("0.00"),
            status="SUBMITTED",
            idempotency_key=idempotency_key,
        )
        db.add(claim)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="submit_claim",
            entity_type="claim",
            entity_id=str(claim.id),
            after={
                "policy_id": policy.id,
                "trigger_code": trigger_code,
                "occurrence_key": occurrence_key,
                "status": claim.status,
            },
        )
        return claim

    @staticmethod
    def evaluate(db: Session, claim_id: int, *, actor: str) -> Claim:
        claim = ClaimsEngine.get(db, claim_id)
        if claim.status not in {"SUBMITTED", "EVALUATING"}:
            raise AppError(
                f"Claim {claim_id} in status {claim.status} cannot be re-evaluated",
                code="invalid_state",
                status_code=409,
            )

        policy = db.get(Policy, claim.policy_id)
        if policy is None:
            raise AppError("Policy missing", code="not_found", status_code=404)

        before_status = claim.status
        claim.status = "EVALUATING"
        db.flush()

        violations = list(
            db.scalars(
                select(Violation)
                .where(Violation.policy_id == policy.id)
                .order_by(Violation.id.asc())
            ).all()
        )
        fraud_signals = list(
            db.scalars(
                select(FraudSignal)
                .where(FraudSignal.shipment_id == claim.shipment_id)
                .order_by(FraudSignal.id.asc())
            ).all()
        )

        policy_snapshot = {
            "id": policy.id,
            "policy_number": policy.policy_number,
            "status": policy.status,
            "coverage_amount": f"{Decimal(policy.coverage_amount):.2f}",
            "currency": policy.currency,
            "coverage_start": _ensure_utc(policy.coverage_start).isoformat(),
            "coverage_end": _ensure_utc(policy.coverage_end).isoformat(),
        }
        violations_snapshot = [
            {
                "id": v.id,
                "trigger_code": v.trigger_code,
                "threshold_value": v.threshold_value,
                "actual_value": v.actual_value,
                "occurred_at": _ensure_utc(v.occurred_at).isoformat(),
            }
            for v in violations
        ]
        fraud_snapshot = [
            {
                "id": f.id,
                "rule_code": f.rule_code,
                "severity": f.severity,
                "score": f"{Decimal(f.score):.2f}",
            }
            for f in fraud_signals
        ]

        decision = compute_pure_claim_decision(
            policy_snapshot=policy_snapshot,
            trigger_code=claim.trigger_code,
            occurrence_key=claim.occurrence_key,
            violations_snapshot=violations_snapshot,
            fraud_snapshot=fraud_snapshot,
        )

        claim.status = decision.status
        claim.approved_amount = decision.approved_amount
        claim.decision_trace = decision.decision_trace
        claim.input_hash = decision.input_hash
        claim.decision_hash = decision.decision_hash
        claim.decided_at = datetime.now(timezone.utc)
        db.flush()

        AuditService.record(
            db,
            actor=actor,
            action="evaluate_claim",
            entity_type="claim",
            entity_id=str(claim.id),
            before={"status": before_status},
            after={
                "status": claim.status,
                "approved_amount": str(claim.approved_amount),
                "decision_hash": claim.decision_hash,
            },
        )
        return claim

    @staticmethod
    def review(
        db: Session,
        claim_id: int,
        *,
        decision: str,
        notes: str,
        actor: str,
    ) -> Claim:
        claim = ClaimsEngine.get(db, claim_id)
        if claim.status != "REVIEW_REQUIRED":
            raise AppError(
                f"Only REVIEW_REQUIRED claims can be reviewed (current: {claim.status})",
                code="invalid_state",
                status_code=409,
            )
        policy = db.get(Policy, claim.policy_id)
        if policy is None:
            raise AppError("Policy missing", code="not_found", status_code=404)

        before_status = claim.status
        claim.status = decision
        claim.reviewer_notes = notes
        claim.decided_at = datetime.now(timezone.utc)
        if decision == "APPROVED":
            claim.approved_amount = Decimal(policy.coverage_amount).quantize(
                Decimal("0.01")
            )
        else:
            claim.approved_amount = Decimal("0.00")

        trace = list(claim.decision_trace or [])
        trace.append(
            {
                "step": "human_review",
                "reviewer": actor,
                "decision": decision,
                "notes": notes,
            }
        )
        claim.decision_trace = trace
        claim.decision_hash = _canonical_hash(
            {
                "input_hash": claim.input_hash,
                "status": claim.status,
                "approved_amount": f"{claim.approved_amount:.2f}",
                "decision_trace": trace,
            }
        )
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="review_claim",
            entity_type="claim",
            entity_id=str(claim.id),
            before={"status": before_status},
            after={"status": claim.status, "notes": notes},
        )
        return claim

    @staticmethod
    def get(db: Session, claim_id: int) -> Claim:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise AppError(
                f"Claim {claim_id} not found",
                code="not_found",
                status_code=404,
            )
        return claim

    @staticmethod
    def list_all(
        db: Session, *, shipment_id: int | None = None, status_filter: str | None = None
    ) -> list[Claim]:
        stmt = select(Claim).order_by(Claim.id.desc())
        if shipment_id is not None:
            stmt = stmt.where(Claim.shipment_id == shipment_id)
        if status_filter is not None:
            stmt = stmt.where(Claim.status == status_filter)
        return list(db.scalars(stmt).all())

