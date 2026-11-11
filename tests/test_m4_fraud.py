from datetime import timedelta

from tests.helpers import create_and_activate_policy, create_parties, create_shipment


def test_scenario_b_style_sensor_manipulation_hard_blocks(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, _, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"], ref="SHIP-B"
    )
    create_and_activate_policy(client, operator_headers, shipment["id"], number="POL-B")
    sim = client.post(
        "/api/v1/simulator/run",
        headers=operator_headers,
        json={"shipment_id": shipment["id"], "seed": 99, "scenario": "B"},
    )
    assert sim.status_code == 201
    client.post(
        "/api/v1/monitoring/evaluate",
        headers=operator_headers,
        json={"shipment_id": shipment["id"]},
    )
    fraud = client.post(
        "/api/v1/fraud/evaluate",
        headers=operator_headers,
        json={"shipment_id": shipment["id"]},
    )
    assert fraud.status_code == 200
    body = fraud.json()
    assert body["has_hard_block"] is True
    rules = {row["rule_code"] for row in body["signals"]}
    assert "STUCK_SENSOR" in rules
    assert "IMPOSSIBLE_TEMP_DELTA" in rules
    assert "GEOFENCE_JUMP" in rules
    for signal in body["signals"]:
        assert signal["explanation"]
        assert signal["evidence_refs"]


def test_document_timestamp_mismatch_hard_block(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, departure, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"], ref="SHIP-DOC"
    )
    from app.services.pdf_fixture import build_simple_pdf

    old_date = (departure - timedelta(days=40)).date().isoformat()
    pdf = build_simple_pdf(
        [
            "ShipmentRef: OTHER-REF",
            f"DocumentDate: {old_date}T00:00:00Z",
        ]
    )
    upload = client.post(
        "/api/v1/evidence/upload",
        headers=operator_headers,
        data={"shipment_id": str(shipment["id"]), "doc_type": "BILL_OF_LADING"},
        files={"file": ("bol.pdf", pdf, "application/pdf")},
    )
    client.post(
        f"/api/v1/evidence/{upload.json()['id']}/extract", headers=operator_headers
    )
    fraud = client.post(
        "/api/v1/fraud/evaluate",
        headers=operator_headers,
        json={"shipment_id": shipment["id"]},
    )
    assert fraud.json()["has_hard_block"] is True
    rules = {row["rule_code"] for row in fraud.json()["signals"]}
    assert "DOCUMENT_MISMATCH" in rules
