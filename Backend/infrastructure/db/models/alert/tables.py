from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.models.base import DataModel


class Alert(DataModel):
    __tablename__ = "alert"
    __table_args__ = {"schema": "alert"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message: Mapped[str] = mapped_column(String, nullable=False)
