from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PayoutExecuteRequest(BaseModel):
    settlement_id: int = Field(gt=0)
    authorization_nonce: str = Field(min_length=8, max_length=64)
    idempotency_key: str = Field(min_length=1, max_length=128)


class PayoutAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payout_id: int
    attempt_number: int
    request_summary: dict[str, Any]
    response_summary: dict[str, Any]
    success: bool
    attempted_at: datetime


class PayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    settlement_id: int
    idempotency_key: str
    provider: str
    external_id: str | None
    status: str
    amount: Decimal
    currency: str
    attempts: int
    created_at: datetime
    updated_at: datetime
    attempt_history: list[PayoutAttemptResponse] = []

