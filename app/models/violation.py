from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), index=True)
    trigger_code: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="BREACH")
    reading_id: Mapped[int | None] = mapped_column(
        ForeignKey("telemetry_readings.id"), nullable=True
    )
    port_delay_id: Mapped[int | None] = mapped_column(
        ForeignKey("port_delays.id"), nullable=True
    )
    threshold_value: Mapped[float] = mapped_column(Float)
    actual_value: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
