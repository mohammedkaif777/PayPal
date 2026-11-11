from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), index=True)
    coverage_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    premium_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    temp_min_c: Mapped[float] = mapped_column()
    temp_max_c: Mapped[float] = mapped_column()
    humidity_max_pct: Mapped[float] = mapped_column()
    delay_hours_max: Mapped[float] = mapped_column()
    geofence_max_km: Mapped[float] = mapped_column(default=100.0)
    coverage_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    coverage_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    supplier_split_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    logistics_split_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
