"""add avatar and vehicle image url

Revision ID: 20260324_0008
Revises: 20260324_0007
Create Date: 2026-03-24 23:50:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from infrastructure.db.models import PG_VIEWS


# revision identifiers, used by Alembic.
revision: str = "20260324_0008"
down_revision: Union[str, Sequence[str], None] = "20260324_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("avatar_image_url", sa.String(), nullable=True),
        schema="user",
    )
    op.add_column(
        "vehicle",
        sa.Column("vehicle_image_url", sa.String(), nullable=True),
        schema="vehicle",
    )

    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))


def downgrade() -> None:
    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    op.drop_column("vehicle", "vehicle_image_url", schema="vehicle")
    op.drop_column("user", "avatar_image_url", schema="user")

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))
