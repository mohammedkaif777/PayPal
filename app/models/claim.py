from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "trigger_code",
            "occurrence_key",
            name="uq_claims_policy_trigger_occurrence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), index=True)
    trigger_code: Mapped[str] = mapped_column(String(32), index=True)
    occurrence_key: Mapped[str] = mapped_column(String(128))
    claimed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    approved_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00")
    )
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED", index=True)
    decision_trace: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

