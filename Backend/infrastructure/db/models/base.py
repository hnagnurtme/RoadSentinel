from datetime import datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import Mapped, declarative_base, mapped_column


metadata = MetaData()
Base = declarative_base(metadata=metadata)


class BaseModel:
    """Common timestamp and soft-delete columns for all persisted models."""

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DataModel(Base, BaseModel):
    __abstract__ = True


class PGView:
    """Simple declarative representation for PostgreSQL view definitions."""

    schema: str
    name: str
    query: str

    @classmethod
    def qualified_name(cls) -> str:
        return f'"{cls.schema}".{cls.name}'

    @classmethod
    def create_sql(cls) -> str:
        return f"CREATE OR REPLACE VIEW {cls.qualified_name()} AS {cls.query.strip()}"

    @classmethod
    def drop_sql(cls) -> str:
        return f"DROP VIEW IF EXISTS {cls.qualified_name()}"
