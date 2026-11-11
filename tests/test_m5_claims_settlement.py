from decimal import Decimal

from app.services.claims import compute_pure_claim_decision
from app.services.settlement import allocate_split
from tests.helpers import create_and_activate_policy, create_parties, create_shipment


def test_allocate_split_sums_exactly():
    supplier, logistics = allocate_split(
        Decimal("10.00"), Decimal("33.33"), Decimal("66.67")
    )
    assert supplier + logistics == Decimal("10.00")
    supplier, logistics = allocate_split(
        Decimal("10000.00"), Decimal("60.00"), Decimal("40.00")
    )
    assert supplier == Decimal("6000.00")
    assert logistics == Decimal("4000.00")


def test_identical_inputs_identical_decision_hash():
    policy = {
        "id": 1,
        "policy_number": "POL-1",
        "status": "TRIGGERED",
        "coverage_amount": "1000.00",
        "currency": "USD",
        "coverage_start": "2026-11-01T00:00:00+00:00",
        "coverage_end": "2026-11-30T00:00:00+00:00",
    }
    violations = [
        {
            "id": 9,
            "trigger_code": "TEMP_HIGH",
            "threshold_value": 8.0,
            "actual_value": 12.0,
            "occurred_at": "2026-11-02T00:00:00+00:00",
        }
    ]
    first = compute_pure_claim_decision(
        policy_snapshot=policy,
        trigger_code="TEMP_HIGH",
        occurrence_key="occ-1",
        violations_snapshot=violations,
        fraud_snapshot=[],
    )
    second = compute_pure_claim_decision(
        policy_snapshot=policy,
        trigger_code="TEMP_HIGH",
        occurrence_key="occ-1",
        violations_snapshot=violations,
        fraud_snapshot=[],
    )
    assert first.decision_hash == second.decision_hash
    assert first.status == "APPROVED"


def test_inactive_policy_and_unmet_trigger_rejected():
    policy = {
        "id": 1,
        "policy_number": "POL-1",
        "status": "DRAFT",
        "coverage_amount": "1000.00",
        "currency": "USD",
        "coverage_start": "2026-11-01T00:00:00+00:00",
        "coverage_end": "2026-11-30T00:00:00+00:00",
    }
    decision = compute_pure_claim_decision(
        policy_snapshot=policy,
        trigger_code="TEMP_HIGH",
        occurrence_key="occ-1",
        violations_snapshot=[],
        fraud_snapshot=[],
    )
    assert decision.status == "REJECTED"
    assert decision.approved_amount == Decimal("0.00")


def test_hard_block_rejects_and_review_routes():
    policy = {
        "id": 1,
        "policy_number": "POL-1",
        "status": "TRIGGERED",
        "coverage_amount": "1000.00",
        "currency": "USD",
        "coverage_start": "2026-11-01T00:00:00+00:00",
        "coverage_end": "2026-11-30T00:00:00+00:00",
    }
    violations = [
        {
            "id": 1,
            "trigger_code": "TEMP_HIGH",
            "threshold_value": 8,
            "actual_value": 12,
            "occurred_at": "2026-11-02T00:00:00+00:00",
        }
    ]
    blocked = compute_pure_claim_decision(
        policy_snapshot=policy,
        trigger_code="TEMP_HIGH",
        occurrence_key="occ-1",
        violations_snapshot=violations,
        fraud_snapshot=[
            {"id": 1, "rule_code": "STUCK_SENSOR", "severity": "HARD_BLOCK", "score": "0.90"}
        ],
    )
    assert blocked.status == "REJECTED"
    review = compute_pure_claim_decision(
        policy_snapshot=policy,
        trigger_code="TEMP_HIGH",
        occurrence_key="occ-1",
        violations_snapshot=violations,
        fraud_snapshot=[
            {"id": 2, "rule_code": "LOW_QUALITY_IMAGE", "severity": "REVIEW", "score": "0.55"}
        ],
    )
    assert review.status == "REVIEW_REQUIRED"


def test_duplicate_claim_occurrence_blocked(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    policy = create_and_activate_policy(client, operator_headers, shipment["id"])
    payload = {
        "policy_id": policy["id"],
        "trigger_code": "TEMP_HIGH",
        "occurrence_key": "same-event",
        "idempotency_key": "claim-1",
    }
    first = client.post("/api/v1/claims", headers=operator_headers, json=payload)
    second = client.post(
        "/api/v1/claims",
        headers=operator_headers,
        json={**payload, "idempotency_key": "claim-2"},
    )
    assert first.status_code == 201
    assert second.status_code == 409
    replay = client.post("/api/v1/claims", headers=operator_headers, json=payload)
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
