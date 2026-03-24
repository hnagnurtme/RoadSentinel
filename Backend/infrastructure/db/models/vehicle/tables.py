from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.models.base import DataModel


class Vehicle(DataModel):
    __tablename__ = "vehicle"
    __table_args__ = {"schema": "vehicle"}

    plate_number: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vehicle_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    production_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vin: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
