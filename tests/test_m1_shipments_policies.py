from tests.helpers import create_and_activate_policy, create_parties, create_shipment


def test_create_list_get_shipment_and_audit(client, operator_headers, admin_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    listed = client.get("/api/v1/shipments", headers=operator_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == shipment["id"]
    fetched = client.get(f"/api/v1/shipments/{shipment['id']}", headers=operator_headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "REGISTERED"
    audit = client.get("/api/v1/audit", headers=admin_headers)
    actions = {row["action"] for row in audit.json()}
    assert "create" in actions


def test_invalid_shipment_transition_rejected(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    response = client.post(
        f"/api/v1/shipments/{shipment['id']}/transition",
        headers=operator_headers,
        json={"status": "CLOSED"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"


def test_policy_lifecycle_and_invalid_cancel_after_settle_path(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    policy = create_and_activate_policy(client, operator_headers, shipment["id"])
    assert policy["status"] == "ACTIVE"
    cancelled = client.post(
        f"/api/v1/policies/{policy['id']}/cancel", headers=operator_headers
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    again = client.post(
        f"/api/v1/policies/{policy['id']}/activate", headers=operator_headers
    )
    assert again.status_code == 409


def test_readonly_cannot_create_shipment(client, readonly_headers, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    response = client.post(
        "/api/v1/shipments",
        headers=readonly_headers,
        json={
            "external_ref": "SHIP-FORBIDDEN",
            "commodity": "Tea",
            "origin_port": "A",
            "destination_port": "B",
            "declared_value": "10.00",
            "supplier_id": supplier["id"],
            "logistics_id": logistics["id"],
            "departure_time": "2026-11-01T00:00:00Z",
            "expected_arrival_time": "2026-11-10T00:00:00Z",
        },
    )
    assert response.status_code == 403


def test_idempotent_shipment_create(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    payload = {
        "external_ref": "SHIP-IDEM",
        "commodity": "Tea",
        "origin_port": "A",
        "destination_port": "B",
        "declared_value": "10.00",
        "supplier_id": supplier["id"],
        "logistics_id": logistics["id"],
        "departure_time": "2026-11-01T00:00:00Z",
        "expected_arrival_time": "2026-11-10T00:00:00Z",
    }
    headers = {**operator_headers, "Idempotency-Key": "ship-key-1"}
    first = client.post("/api/v1/shipments", headers=headers, json=payload)
    second = client.post("/api/v1/shipments", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
