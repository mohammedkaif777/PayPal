from decimal import Decimal

from app.db.session import SessionLocal
from app.services.payment import MockPaymentProvider
from app.services.payout import PayoutService
from tests.helpers import create_and_activate_policy, create_parties, create_shipment


def _approved_claim_ready_for_payout(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, departure, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"], ref="SHIP-PAY"
    )
    policy = create_and_activate_policy(
        client, operator_headers, shipment["id"], number="POL-PAY", coverage="100.01"
    )
    ingest = client.post(
        "/api/v1/telemetry/ingest",
        headers=operator_headers,
        json={
            "shipment_id": shipment["id"],
            "readings": [
                {
                    "device_id": "DEV-1",
                    "recorded_at": departure.isoformat(),
                    "temperature_c": 19.0,
                    "humidity_pct": 50.0,
                    "latitude": 19.0760,
                    "longitude": 72.8777,
                }
            ],
        },
    )
    assert ingest.status_code == 201
    client.post(
        "/api/v1/monitoring/evaluate",
        headers=operator_headers,
        json={"shipment_id": shipment["id"]},
    )
    client.post(
        "/api/v1/fraud/evaluate",
        headers=operator_headers,
        json={"shipment_id": shipment["id"]},
    )
    claim = client.post(
        "/api/v1/claims",
        headers=operator_headers,
        json={
            "policy_id": policy["id"],
            "trigger_code": "TEMP_HIGH",
            "occurrence_key": "heat-1",
            "idempotency_key": "claim-pay-1",
        },
    )
    evaluated = client.post(
        f"/api/v1/claims/{claim.json()['id']}/evaluate", headers=operator_headers
    )
    assert evaluated.json()["status"] == "APPROVED"
    settlement = client.post(
        "/api/v1/settlements",
        headers=operator_headers,
        json={"claim_id": claim.json()["id"]},
    )
    assert settlement.status_code == 201
    total = Decimal(settlement.json()["supplier_amount"]) + Decimal(
        settlement.json()["logistics_amount"]
    )
    assert total == Decimal(settlement.json()["total_amount"])
    return settlement.json()


def test_mock_payout_success_and_duplicate_blocked(client, operator_headers):
    settlement = _approved_claim_ready_for_payout(client, operator_headers)
    payout = client.post(
        "/api/v1/payouts",
        headers=operator_headers,
        json={
            "settlement_id": settlement["id"],
            "authorization_nonce": settlement["authorization_nonce"],
            "idempotency_key": "payout-1",
        },
    )
    assert payout.status_code == 201
    assert payout.json()["status"] == "SUCCEEDED"
    replay = client.post(
        "/api/v1/payouts",
        headers=operator_headers,
        json={
            "settlement_id": settlement["id"],
            "authorization_nonce": settlement["authorization_nonce"],
            "idempotency_key": "payout-1",
        },
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == payout.json()["id"]
    other_key = client.post(
        "/api/v1/payouts",
        headers=operator_headers,
        json={
            "settlement_id": settlement["id"],
            "authorization_nonce": settlement["authorization_nonce"],
            "idempotency_key": "payout-2",
        },
    )
    assert other_key.status_code == 409


def test_invalid_nonce_cannot_be_paid(client, operator_headers):
    settlement = _approved_claim_ready_for_payout(client, operator_headers)
    response = client.post(
        "/api/v1/payouts",
        headers=operator_headers,
        json={
            "settlement_id": settlement["id"],
            "authorization_nonce": "deadbeefdeadbeef",
            "idempotency_key": "payout-bad",
        },
    )
    assert response.status_code == 403


def test_failed_payout_retries_same_idempotency_key(client, operator_headers):
    settlement = _approved_claim_ready_for_payout(client, operator_headers)
    with SessionLocal() as db:
        payout, attempts = PayoutService.execute_payout(
            db,
            settlement_id=settlement["id"],
            authorization_nonce=settlement["authorization_nonce"],
            idempotency_key="payout-retry",
            actor="operator",
            adapter=MockPaymentProvider(force_fail=True),
        )
        assert payout.status == "FAILED"
        assert attempts[0].request_summary["idempotency_key"] == "payout-retry"
        retried, retry_attempts = PayoutService.retry_payout(
            db,
            payout.id,
            actor="operator",
            adapter=MockPaymentProvider(force_fail=False),
        )
        db.commit()
        assert retried.status == "SUCCEEDED"
        assert retried.attempts == 2
        assert retry_attempts[-1].request_summary["idempotency_key"] == "payout-retry"
        assert retry_attempts[0].request_summary["idempotency_key"] == (
            retry_attempts[1].request_summary["idempotency_key"]
        )
