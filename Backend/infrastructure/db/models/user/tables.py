from typing import Optional

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.models.base import DataModel


class User(DataModel):
    __tablename__ = "user"
    __table_args__ = {"schema": "user"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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
