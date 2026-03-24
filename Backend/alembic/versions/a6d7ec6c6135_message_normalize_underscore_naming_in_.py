"""message=normalize underscore naming in views

Revision ID: a6d7ec6c6135
Revises: 20260324_0005
Create Date: 2026-03-24 22:10:09.221721

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'a6d7ec6c6135'
down_revision = '20260324_0005'
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

