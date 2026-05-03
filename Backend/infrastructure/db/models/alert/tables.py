import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from datetime import datetime
from infrastructure.db.models.base import DataModel

"""Enum mirrored from the domain layer for SQLAlchemy mapping."""


class AlertType(str, Enum):
    SLEEPING = "SLEEPING"
    USING_PHONE = "USING_PHONE"
    DISTRACTED = "DISTRACTED"


class Alert(DataModel):
    __tablename__ = "alert"
    __table_args__ = {"schema": "alert"}

    message: Mapped[str] = mapped_column(String, nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, name="alert_type_enum", schema="alert"),
        nullable=False,
        default=AlertType.DISTRACTED,
    )
    evidence_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    vehicle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
class AppealStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class Appeal(DataModel):
    __tablename__ = "appeal"
    __table_args__ = {"schema": "alert"}
    
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[AppealStatus] = mapped_column(
        SAEnum(AppealStatus, name="appeal_status_enum", schema="alert"),
        nullable=False,
        default=AppealStatus.PENDING,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)