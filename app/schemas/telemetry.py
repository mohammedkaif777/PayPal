from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryPointIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    recorded_at: datetime
    temperature_c: float = Field(ge=-80.0, le=80.0)
    humidity_pct: float = Field(ge=0.0, le=100.0)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    source: str = Field(default="iot_sensor", min_length=1, max_length=64)

    @field_validator("recorded_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        ts = (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )
        min_ts = datetime(2000, 1, 1, tzinfo=timezone.utc)
        max_ts = datetime.now(timezone.utc) + timedelta(days=1)
        if ts < min_ts or ts > max_ts:
            raise ValueError("recorded_at timestamp is outside valid bounds")
        return ts


class TelemetryBulkIngestRequest(BaseModel):
    shipment_id: int = Field(gt=0)
    readings: list[TelemetryPointIn] = Field(min_length=1, max_length=1000)


class TelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    device_id: str
    recorded_at: datetime
    temperature_c: float
    humidity_pct: float
    latitude: float
    longitude: float
    source: str
    created_at: datetime


class TelemetryBulkIngestResponse(BaseModel):
    shipment_id: int
    ingested_count: int
    duplicate_skipped_count: int
