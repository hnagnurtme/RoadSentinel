"""refresh views

Revision ID: 9bd671df154f
Revises: b86cf1f0dd45
Create Date: 2026-05-06 05:22:22.057256

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9bd671df154f"
down_revision = "b86cf1f0dd45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from infrastructure.db.models import PG_VIEWS

    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))


def downgrade() -> None:
    from infrastructure.db.models import PG_VIEWS

    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))
