from typing import Any, Literal

from pydantic import BaseModel, Field


class ScenarioRunRequest(BaseModel):
    scenario: Literal["A", "B"] = "A"
    seed: int = Field(default=42)


class ScenarioRunResponse(BaseModel):
    scenario: str
    seed: int
    shipment_id: int
    policy_id: int
    claim_id: int | None = None
    settlement_id: int | None = None
    payout_id: int | None = None
    claim_status: str | None = None
    payout_status: str | None = None
    hard_block: bool = False
    summary: dict[str, Any]
