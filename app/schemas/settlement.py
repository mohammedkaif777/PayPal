from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SettlementCreateRequest(BaseModel):
    claim_id: int = Field(gt=0)


class SettlementLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    settlement_id: int
    party_id: int
    role: str
    recipient_email: str
    amount: Decimal


class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim_id: int
    total_amount: Decimal
    currency: str
    supplier_amount: Decimal
    logistics_amount: Decimal
    authorization_nonce: str
    authorization_hash: str
    nonce_used: bool
    settled_at: datetime
    lines: list[SettlementLineResponse] = []

