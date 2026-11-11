from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id"), unique=True, index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    supplier_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    logistics_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    authorization_nonce: Mapped[str] = mapped_column(String(64), unique=True)
    authorization_hash: Mapped[str] = mapped_column(String(64))
    nonce_used: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SettlementLine(Base):
    __tablename__ = "settlement_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("settlements.id"), index=True
    )
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    recipient_email: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))

