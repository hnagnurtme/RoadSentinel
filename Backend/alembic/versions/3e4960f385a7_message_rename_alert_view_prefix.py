"""message=rename alert view prefix

Revision ID: 3e4960f385a7
Revises: 169d289450c4
Create Date: 2026-03-24 21:37:10.603322

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '3e4960f385a7'
down_revision = '169d289450c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from infrastructure.db.models import PG_VIEWS

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))



def downgrade() -> None:
    from infrastructure.db.models import PG_VIEWS

    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

