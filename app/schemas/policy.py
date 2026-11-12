from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PolicyCreate(BaseModel):
    policy_number: str = Field(min_length=2, max_length=64)
    shipment_id: int = Field(gt=0)
    coverage_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    premium_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    temp_min_c: float = Field(ge=-80.0, le=80.0)
    temp_max_c: float = Field(ge=-80.0, le=80.0)
    humidity_max_pct: float = Field(gt=0.0, le=100.0)
    delay_hours_max: float = Field(gt=0.0)
    geofence_max_km: float = Field(default=100.0, gt=0.0)
    coverage_start: datetime
    coverage_end: datetime
    supplier_split_pct: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    logistics_split_pct: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    version: int = Field(default=1, ge=1)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("coverage_start", "coverage_end")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_policy_terms(self) -> "PolicyCreate":
        if self.temp_min_c >= self.temp_max_c:
            raise ValueError("temp_min_c must be strictly less than temp_max_c")
        if self.coverage_end <= self.coverage_start:
            raise ValueError("coverage_end must be after coverage_start")
        if (self.supplier_split_pct + self.logistics_split_pct) != Decimal("100.00") and (
            self.supplier_split_pct + self.logistics_split_pct
        ) != Decimal("100"):
            raise ValueError("supplier_split_pct + logistics_split_pct must equal 100")
        return self


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_number: str
    shipment_id: int
    coverage_amount: Decimal
    premium_amount: Decimal
    currency: str
    temp_min_c: float
    temp_max_c: float
    humidity_max_pct: float
    delay_hours_max: float
    geofence_max_km: float
    coverage_start: datetime
    coverage_end: datetime
    supplier_split_pct: Decimal
    logistics_split_pct: Decimal
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
