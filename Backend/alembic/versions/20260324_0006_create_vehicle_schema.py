"""create vehicle schema

Revision ID: 20260324_0006
Revises: a6d7ec6c6135
Create Date: 2026-03-24 22:45:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from infrastructure.db.models import PG_VIEWS


# revision identifiers, used by Alembic.
revision: str = "20260324_0006"
down_revision: Union[str, Sequence[str], None] = "a6d7ec6c6135"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "vehicle"'))

    op.create_table(
        "vehicle",
        sa.Column(
            "_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("plate_number", sa.String(), nullable=False),
        sa.Column("manufacturer", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("production_year", sa.Integer(), nullable=True),
        sa.Column("vin", sa.String(), nullable=True),
        sa.Column("_created_at", sa.DateTime(), nullable=False),
        sa.Column("_updated_at", sa.DateTime(), nullable=False),
        sa.Column("_deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("_id", name="vehicle_pkey"),
        schema="vehicle",
    )
    op.create_index(
        op.f("ix_vehicle_vehicle__id"),
        "vehicle",
        ["_id"],
        unique=False,
        schema="vehicle",
    )
    op.create_index(
        op.f("ix_vehicle_vehicle_plate_number"),
        "vehicle",
        ["plate_number"],
        unique=True,
        schema="vehicle",
    )
    op.create_unique_constraint(
        op.f("uq_vehicle_vehicle_vin"),
        "vehicle",
        ["vin"],
        schema="vehicle",
    )

    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))
    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))


def downgrade() -> None:
    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    op.drop_constraint(
        op.f("uq_vehicle_vehicle_vin"), "vehicle", schema="vehicle", type_="unique"
    )
    op.drop_index(
        op.f("ix_vehicle_vehicle_plate_number"), table_name="vehicle", schema="vehicle"
    )
    op.drop_index(
        op.f("ix_vehicle_vehicle__id"), table_name="vehicle", schema="vehicle"
    )
    op.drop_table("vehicle", schema="vehicle")

    op.execute(sa.text('DROP SCHEMA IF EXISTS "vehicle"'))

    for view_def in PG_VIEWS:
        if view_def.name != "_vehicle_overview":
            op.execute(sa.text(view_def.create_sql()))
