from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, MetaData
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declarative_base, mapped_column


metadata = MetaData()
Base = declarative_base(metadata=metadata)


class DataModel(Base):
    """Common timestamp and soft-delete columns for all persisted models."""

    __abstract__ = True

    _id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    _created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    _updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    _deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
