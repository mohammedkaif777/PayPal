from datetime import datetime, timedelta, timezone

from app.services.simulator import DeterministicSimulator
from tests.helpers import create_and_activate_policy, create_parties, create_shipment


def test_temperature_humidity_geofence_and_delay_violations(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, departure, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    policy = create_and_activate_policy(client, operator_headers, shipment["id"])
    ts = departure + timedelta(minutes=30)
    ingest = client.post(
        "/api/v1/telemetry/ingest",
        headers=operator_headers,
        json={
            "shipment_id": shipment["id"],
            "readings": [
                {
                    "device_id": "DEV-1",
                    "recorded_at": ts.isoformat(),
                    "temperature_c": 18.5,
                    "humidity_pct": 95.0,
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "source": "iot_sensor",
                }
            ],
        },
    )
    assert ingest.status_code == 201
    delay = client.post(
        "/api/v1/telemetry/port-delays",
        headers=operator_headers,
        json={
            "shipment_id": shipment["id"],
            "port_name": "Mumbai",
            "delay_hours": "72.00",
            "reported_at": ts.isoformat(),
        },
    )
    assert delay.status_code == 201
    evaluated = client.post(
        "/api/v1/monitoring/evaluate",
        headers=operator_headers,
        json={"shipment_id": shipment["id"], "policy_id": policy["id"]},
    )
    assert evaluated.status_code == 200
    codes = {row["trigger_code"] for row in evaluated.json()}
    assert "TEMP_HIGH" in codes
    assert "HUMIDITY_HIGH" in codes
    assert "GEOFENCE_BREACH" in codes
    assert "PORT_DELAY" in codes


def test_invalid_telemetry_range_rejected(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, departure, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    response = client.post(
        "/api/v1/telemetry/ingest",
        headers=operator_headers,
        json={
            "shipment_id": shipment["id"],
            "readings": [
                {
                    "device_id": "DEV-1",
                    "recorded_at": departure.isoformat(),
                    "temperature_c": 400.0,
                    "humidity_pct": 10.0,
                    "latitude": 1.0,
                    "longitude": 1.0,
                }
            ],
        },
    )
    assert response.status_code == 422


def test_duplicate_timestamps_skipped(client, operator_headers):
    supplier, logistics = create_parties(client, operator_headers)
    shipment, departure, _ = create_shipment(
        client, operator_headers, supplier["id"], logistics["id"]
    )
    point = {
        "device_id": "DEV-1",
        "recorded_at": departure.isoformat(),
        "temperature_c": 4.0,
        "humidity_pct": 60.0,
        "latitude": 19.07,
        "longitude": 72.87,
    }
    first = client.post(
        "/api/v1/telemetry/ingest",
        headers=operator_headers,
        json={"shipment_id": shipment["id"], "readings": [point, point]},
    )
    assert first.json()["ingested_count"] == 1
    assert first.json()["duplicate_skipped_count"] == 1


def test_seeded_simulator_is_deterministic():
    start = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
    a = DeterministicSimulator.generate_series(seed=42, start_time=start, scenario="A")
    b = DeterministicSimulator.generate_series(seed=42, start_time=start, scenario="A")
    assert [p.model_dump() for p in a] == [p.model_dump() for p in b]
    c = DeterministicSimulator.generate_series(seed=7, start_time=start, scenario="A")
    assert [p.temperature_c for p in a] != [p.temperature_c for p in c]
