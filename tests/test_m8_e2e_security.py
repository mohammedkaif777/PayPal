def test_scenario_a_end_to_end_valid_claim_pays_once(client, operator_headers, admin_headers):
    resp = client.post(
        "/api/v1/scenarios/run",
        headers=operator_headers,
        json={"scenario": "A", "seed": 2026},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["claim_status"] == "PAID"
    assert body["hard_block"] is False
    assert body["settlement_id"] is not None
    assert body["payout_id"] is not None
    assert body["payout_status"] == "SUCCEEDED"

    settlement = client.get(
        f"/api/v1/settlements/{body['settlement_id']}", headers=operator_headers
    ).json()
    assert float(settlement["supplier_amount"]) + float(settlement["logistics_amount"]) == float(
        settlement["total_amount"]
    )
    assert settlement["nonce_used"] is True

    # Audit log contains full hash-chained trail
    audit = client.get("/api/v1/audit?limit=50", headers=admin_headers)
    assert audit.status_code == 200
    assert len(audit.json()) >= 5


def test_scenario_b_end_to_end_fraud_produces_no_payout(client, operator_headers):
    resp = client.post(
        "/api/v1/scenarios/run",
        headers=operator_headers,
        json={"scenario": "B", "seed": 2026},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["claim_status"] == "REJECTED"
    assert body["hard_block"] is True
    assert len(body["summary"]["fraud_rules"]) >= 2
    assert body["settlement_id"] is None
    assert body["payout_id"] is None
    assert body["payout_status"] is None
