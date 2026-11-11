from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    role: Literal["supplier", "logistics"]
    payout_email: str = Field(min_length=3, max_length=255)
    country_code: str = Field(default="US", min_length=2, max_length=8)

    @field_validator("payout_email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or "." not in cleaned.split("@", 1)[-1]:
            raise ValueError("Invalid payout email format")
        return cleaned


class PartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str
    payout_email: str
    country_code: str
    created_at: datetime
