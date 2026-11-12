from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    commodity: Mapped[str] = mapped_column(String(128))
    origin_port: Mapped[str] = mapped_column(String(128))
    destination_port: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(32), default="SEA")
    declared_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    supplier_id: Mapped[int] = mapped_column(ForeignKey("parties.id"), index=True)
    logistics_id: Mapped[int] = mapped_column(ForeignKey("parties.id"), index=True)
    route_waypoints: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expected_arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_arrival_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="REGISTERED", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
