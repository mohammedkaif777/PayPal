from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PortDelayCreate(BaseModel):
    shipment_id: int = Field(gt=0)
    port_name: str = Field(min_length=1, max_length=128)
    delay_hours: Decimal = Field(ge=0, max_digits=8, decimal_places=2)
    reported_at: datetime
    source: str = Field(default="port_authority", min_length=1, max_length=64)

    @field_validator("reported_at")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class PortDelayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    port_name: str
    delay_hours: Decimal
    reported_at: datetime
    source: str
    created_at: datetime
