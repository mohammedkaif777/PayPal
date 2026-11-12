from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ViolationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    policy_id: int
    trigger_code: str
    severity: str
    reading_id: int | None
    port_delay_id: int | None
    threshold_value: float
    actual_value: float
    explanation: str
    occurred_at: datetime
    detected_at: datetime


class MonitoringEvaluateRequest(BaseModel):
    shipment_id: int = Field(gt=0)
    policy_id: int | None = Field(default=None, gt=0)


class SimulationRequest(BaseModel):
    shipment_id: int = Field(gt=0)
    seed: int = Field(default=42)
    num_readings: int = Field(default=12, ge=3, le=200)
    scenario: Literal["A", "B"] = "A"
    device_id: str = Field(default="IOT-SENSOR-01", min_length=1, max_length=64)
