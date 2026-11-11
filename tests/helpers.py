from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image


def png_bytes(color: tuple[int, int, int] = (30, 140, 80)) -> bytes:
    image = Image.new("RGB", (96, 64), color=color)
    for y in range(0, 64, 6):
        for x in range(96):
            image.putpixel((x, y), (255, 255, 255))
    for x in range(0, 96, 6):
        for y in range(64):
            image.putpixel((x, y), (15, 25, 40))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def future_window():
    now = datetime.now(timezone.utc)
    departure = now - timedelta(hours=4)
    arrival = now + timedelta(days=5)
    return departure, arrival


def create_parties(client, headers):
    supplier = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "name": "AgriFresh Farms",
            "role": "supplier",
            "payout_email": "supplier@sandbox.example",
        },
    )
    logistics = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "name": "ColdChain Logistics",
            "role": "logistics",
            "payout_email": "logistics@sandbox.example",
        },
    )
    assert supplier.status_code == 201, supplier.text
    assert logistics.status_code == 201, logistics.text
    return supplier.json(), logistics.json()


def create_shipment(client, headers, supplier_id: int, logistics_id: int, ref="SHIP-001"):
    departure, arrival = future_window()
    response = client.post(
        "/api/v1/shipments",
        headers=headers,
        json={
            "external_ref": ref,
            "commodity": "Fresh Mangoes",
            "origin_port": "Mumbai",
            "destination_port": "Rotterdam",
            "mode": "SEA",
            "declared_value": "25000.00",
            "currency": "USD",
            "supplier_id": supplier_id,
            "logistics_id": logistics_id,
            "route_waypoints": [
                {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777},
                {"name": "Rotterdam", "latitude": 51.9225, "longitude": 4.4792},
            ],
            "departure_time": departure.isoformat(),
            "expected_arrival_time": arrival.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json(), departure, arrival


def create_and_activate_policy(
    client, headers, shipment_id: int, number="POL-001", coverage="1000.00"
):
    departure, arrival = future_window()
    response = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "policy_number": number,
            "shipment_id": shipment_id,
            "coverage_amount": coverage,
            "premium_amount": "25.00",
            "currency": "USD",
            "temp_min_c": 1.0,
            "temp_max_c": 8.0,
            "humidity_max_pct": 80.0,
            "delay_hours_max": 24.0,
            "geofence_max_km": 100.0,
            "coverage_start": (departure - timedelta(hours=1)).isoformat(),
            "coverage_end": (arrival + timedelta(days=1)).isoformat(),
            "supplier_split_pct": "60.00",
            "logistics_split_pct": "40.00",
        },
    )
    assert response.status_code == 201, response.text
    activated = client.post(
        f"/api/v1/policies/{response.json()['id']}/activate", headers=headers
    )
    assert activated.status_code == 200, activated.text
    return activated.json()
