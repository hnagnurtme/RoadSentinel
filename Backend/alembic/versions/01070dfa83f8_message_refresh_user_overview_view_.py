"""message=refresh user overview view columns

Revision ID: 01070dfa83f8
Revises: 11c76830e642
Create Date: 2026-03-24 21:54:29.744378

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "01070dfa83f8"
down_revision = "11c76830e642"
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
