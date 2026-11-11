from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Waypoint(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class ShipmentCreate(BaseModel):
    external_ref: str = Field(min_length=2, max_length=64)
    commodity: str = Field(min_length=1, max_length=128)
    origin_port: str = Field(min_length=1, max_length=128)
    destination_port: str = Field(min_length=1, max_length=128)
    mode: Literal["SEA", "AIR", "ROAD", "RAIL"] = "SEA"
    declared_value: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    supplier_id: int = Field(gt=0)
    logistics_id: int = Field(gt=0)
    route_waypoints: list[Waypoint] | None = None
    departure_time: datetime
    expected_arrival_time: datetime

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("departure_time", "expected_arrival_time")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_dates(self) -> "ShipmentCreate":
        if self.expected_arrival_time <= self.departure_time:
            raise ValueError("expected_arrival_time must be after departure_time")
        return self


class ShipmentStatusUpdate(BaseModel):
    status: Literal["IN_TRANSIT", "DELIVERED", "CLOSED", "CANCELLED"]
    actual_arrival_time: datetime | None = None

    @field_validator("actual_arrival_time")
    @classmethod
    def ensure_utc_optional(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_ref: str
    commodity: str
    origin_port: str
    destination_port: str
    mode: str
    declared_value: Decimal
    currency: str
    supplier_id: int
    logistics_id: int
    route_waypoints: list[dict] | None
    departure_time: datetime
    expected_arrival_time: datetime
    actual_arrival_time: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime
