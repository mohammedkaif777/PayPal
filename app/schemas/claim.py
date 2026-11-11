from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClaimSubmitRequest(BaseModel):
    policy_id: int = Field(gt=0)
    trigger_code: Literal[
        "TEMP_HIGH", "TEMP_LOW", "HUMIDITY_HIGH", "GEOFENCE_BREACH", "PORT_DELAY"
    ]
    occurrence_key: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ClaimReviewRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    notes: str = Field(min_length=3, max_length=1000)


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    shipment_id: int
    trigger_code: str
    occurrence_key: str
    claimed_amount: Decimal
    approved_amount: Decimal
    status: str
    decision_trace: list[dict[str, Any]] | None
    input_hash: str | None
    decision_hash: str | None
    idempotency_key: str
    reviewer_notes: str | None
    submitted_at: datetime
    decided_at: datetime | None

