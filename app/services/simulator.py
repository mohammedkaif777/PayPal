import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.shipment import Shipment
from app.schemas.telemetry import TelemetryBulkIngestRequest, TelemetryPointIn
from app.services.telemetry import TelemetryService


class DeterministicSimulator:
    @staticmethod
    def generate_series(
        *,
        seed: int,
        start_time: datetime,
        num_readings: int = 12,
        scenario: str = "A",
        device_id: str = "IOT-SENSOR-01",
        base_lat: float = 19.0760,
        base_lon: float = 72.8777,
    ) -> list[TelemetryPointIn]:
        rng = random.Random(seed)
        t0 = (
            start_time.replace(tzinfo=timezone.utc)
            if start_time.tzinfo is None
            else start_time.astimezone(timezone.utc)
        )
        points: list[TelemetryPointIn] = []

        for idx in range(num_readings):
            ts = t0 + timedelta(minutes=15 * idx)
            if scenario == "A":
                # Realistic cold-chain shipment with a genuine cooling-unit failure mid-transit
                if idx < num_readings // 2:
                    temp = round(4.0 + rng.uniform(-0.4, 0.5), 2)
                else:
                    # Gradual heat excursion above typical 8C max threshold
                    temp = round(9.5 + (idx - num_readings // 2) * 0.45 + rng.uniform(-0.2, 0.3), 2)
                humidity = round(68.0 + rng.uniform(-2.5, 2.5), 2)
                lat = round(base_lat + idx * 0.01 + rng.uniform(-0.002, 0.002), 5)
                lon = round(base_lon + idx * 0.015 + rng.uniform(-0.002, 0.002), 5)
            else:
                # Scenario B: Manipulated / spoofed telemetry
                # - Humidity flatlined at exactly 50.0%
                # - Impossibly flat temperature then sudden +35C spike, plus geofence teleport
                if idx < num_readings - 2:
                    temp = 4.00
                elif idx == num_readings - 2:
                    temp = 39.50
                else:
                    temp = 4.00
                humidity = 50.0
                if idx == num_readings - 2:
                    lat = round(base_lat + 8.0, 5)
                    lon = round(base_lon + 8.0, 5)
                else:
                    lat = round(base_lat + idx * 0.01, 5)
                    lon = round(base_lon + idx * 0.01, 5)

            points.append(
                TelemetryPointIn(
                    device_id=device_id,
                    recorded_at=ts,
                    temperature_c=temp,
                    humidity_pct=humidity,
                    latitude=max(-90.0, min(90.0, lat)),
                    longitude=max(-180.0, min(180.0, lon)),
                    source=f"sim_{scenario.lower()}_seed_{seed}",
                )
            )
        return points

    @staticmethod
    def run_for_shipment(
        db: Session,
        *,
        shipment_id: int,
        seed: int = 42,
        num_readings: int = 12,
        scenario: str = "A",
        device_id: str = "IOT-SENSOR-01",
        actor: str = "simulator",
    ) -> tuple[int, int]:
        shipment = db.get(Shipment, shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {shipment_id} not found",
                code="not_found",
                status_code=404,
            )

        base_lat, base_lon = 19.0760, 72.8777
        if shipment.route_waypoints:
            base_lat = float(shipment.route_waypoints[0]["latitude"])
            base_lon = float(shipment.route_waypoints[0]["longitude"])

        points = DeterministicSimulator.generate_series(
            seed=seed,
            start_time=shipment.departure_time,
            num_readings=num_readings,
            scenario=scenario,
            device_id=device_id,
            base_lat=base_lat,
            base_lon=base_lon,
        )
        return TelemetryService.bulk_ingest(
            db,
            TelemetryBulkIngestRequest(shipment_id=shipment_id, readings=points),
            actor=actor,
        )
