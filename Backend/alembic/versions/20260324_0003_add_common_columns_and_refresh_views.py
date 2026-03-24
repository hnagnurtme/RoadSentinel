"""add common columns and refresh views

Revision ID: 20260324_0003
Revises: 20260324_0002
Create Date: 2026-03-24 01:10:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from infrastructure.db.models import PG_VIEWS


# revision identifiers, used by Alembic.
revision: str = "20260324_0003"
down_revision: Union[str, Sequence[str], None] = "20260324_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for schema_name, table_name in (("user", "user"), ("alert", "alert")):
        op.execute(
            sa.text(
                f'ALTER TABLE "{schema_name}"."{table_name}" '
                "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE"
            )
        )
        op.execute(
            sa.text(
                f'ALTER TABLE "{schema_name}"."{table_name}" '
                "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE"
            )
        )
        op.execute(
            sa.text(
                f'UPDATE "{schema_name}"."{table_name}" '
                "SET updated_at = COALESCE(updated_at, created_at)"
            )
        )
        op.execute(
            sa.text(
                f'ALTER TABLE "{schema_name}"."{table_name}" '
                "ALTER COLUMN updated_at SET NOT NULL"
            )
        )

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW "user"._user_overview AS
            SELECT
                u.id,
                u.email,
                u.name,
                u.created_at
            FROM "user"."user" u
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW "alert"._alert_overview AS
            SELECT
                a.id,
                a.message,
                length(a.message) AS message_length,
                a.created_at
            FROM "alert".alert a
            """
        )
    )

    op.execute(sa.text('ALTER TABLE "alert"."alert" DROP COLUMN IF EXISTS deleted_at'))
    op.execute(sa.text('ALTER TABLE "alert"."alert" DROP COLUMN IF EXISTS updated_at'))
    op.execute(sa.text('ALTER TABLE "user"."user" DROP COLUMN IF EXISTS deleted_at'))
    op.execute(sa.text('ALTER TABLE "user"."user" DROP COLUMN IF EXISTS updated_at'))
