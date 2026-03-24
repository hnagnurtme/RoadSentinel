"""init schemas and tables

Revision ID: 20260324_0001
Revises:
Create Date: 2026-03-24 00:01:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260324_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "user"'))
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "alert"'))

    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema="user",
    )
    op.create_index(
        op.f("ix_user_user_email"), "user", ["email"], unique=False, schema="user"
    )
    op.create_index(
        op.f("ix_user_user_id"), "user", ["id"], unique=False, schema="user"
    )

    op.create_table(
        "alert",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="alert",
    )
    op.create_index(
        op.f("ix_alert_alert_id"), "alert", ["id"], unique=False, schema="alert"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_alert_alert_id"), table_name="alert", schema="alert")
    op.drop_table("alert", schema="alert")

    op.drop_index(op.f("ix_user_user_id"), table_name="user", schema="user")
    op.drop_index(op.f("ix_user_user_email"), table_name="user", schema="user")
    op.drop_table("user", schema="user")

    op.execute(sa.text('DROP SCHEMA IF EXISTS "alert"'))
    op.execute(sa.text('DROP SCHEMA IF EXISTS "user"'))
