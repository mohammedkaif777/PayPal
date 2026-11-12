def test_scenario_a_valid_claim_pays_split_once(client, operator_headers):
    first = client.post(
        "/api/v1/scenarios/run",
        headers=operator_headers,
        json={"scenario": "A", "seed": 42},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["claim_status"] == "PAID"
    assert body["payout_status"] == "SUCCEEDED"
    assert body["hard_block"] is False
    settlement = client.get(
        f"/api/v1/settlements/{body['settlement_id']}", headers=operator_headers
    )
    data = settlement.json()
    from decimal import Decimal

    assert Decimal(data["supplier_amount"]) + Decimal(data["logistics_amount"]) == Decimal(
        data["total_amount"]
    )
    duplicate = client.post(
        "/api/v1/payouts",
        headers=operator_headers,
        json={
            "settlement_id": body["settlement_id"],
            "authorization_nonce": data["authorization_nonce"],
            "idempotency_key": "another-payout",
        },
    )
    assert duplicate.status_code == 409


def test_scenario_b_fraud_claim_produces_no_payout(client, operator_headers):
    response = client.post(
        "/api/v1/scenarios/run",
        headers=operator_headers,
        json={"scenario": "B", "seed": 99},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["hard_block"] is True
    assert body["claim_status"] == "REJECTED"
    assert body["payout_id"] is None
    payouts = client.get("/api/v1/payouts", headers=operator_headers)
    assert payouts.json() == []


def test_unauthenticated_domain_routes_rejected(client):
    assert client.get("/api/v1/shipments").status_code == 401
    assert client.post("/api/v1/scenarios/run", json={"scenario": "A"}).status_code == 401
