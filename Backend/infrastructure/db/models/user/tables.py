import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Date, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.models.base import DataModel


class User(DataModel):
    __tablename__ = "user"
    __table_args__ = {"schema": "user"}

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name__family: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name__given: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name__middle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name__prefix: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name__suffix: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    birthday: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address__city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address__country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address__line1: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address__line2: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="driver")
    fingerprint_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)

class DrivingSession(DataModel):
    __tablename__ = "driving_session"
    __table_args__ = {"schema": "user"}

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user._id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE") # ACTIVE, COMPLETED
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
