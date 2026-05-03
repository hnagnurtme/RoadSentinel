from typing import Optional

from sqlalchemy import Date, String
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
