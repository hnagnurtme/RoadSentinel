"""create schema views

Revision ID: 20260324_0002
Revises: 20260324_0001
Create Date: 2026-03-24 00:20:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260324_0002"
down_revision: Union[str, Sequence[str], None] = "20260324_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW \"user\".v_user_overview AS
            SELECT
                u.id,
                u.email,
                u.name,
                u.created_at
            FROM \"user\".\"user\" u
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW \"alert\".v_alert_overview AS
            SELECT
                a.id,
                a.message,
                length(a.message) AS message_length,
                a.created_at
            FROM \"alert\".alert a
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text('DROP VIEW IF EXISTS "alert".v_alert_overview'))
    op.execute(sa.text('DROP VIEW IF EXISTS "user".v_user_overview'))
