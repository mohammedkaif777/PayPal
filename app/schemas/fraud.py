from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VerificationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    document_id: int | None
    check_code: str
    passed: bool
    details: dict[str, Any]
    checked_at: datetime


class FraudSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    rule_code: str
    severity: str
    score: Decimal
    explanation: str
    evidence_refs: dict[str, Any]
    detected_at: datetime


class FraudEvaluateRequest(BaseModel):
    shipment_id: int = Field(gt=0)


class FraudEvaluateResponse(BaseModel):
    shipment_id: int
    verifications: list[VerificationResultResponse]
    signals: list[FraudSignalResponse]
    has_hard_block: bool
    requires_review: bool

