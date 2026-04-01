"""auto

Revision ID: 71a60d2ea520
Revises: 20260324_0001
Create Date: 2026-04-01 23:02:33.515036

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "71a60d2ea520"
down_revision = "20260324_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "user"'))
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "alert"'))
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "vehicle"'))

    from infrastructure.db.models import Base, PG_VIEWS

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))


def downgrade() -> None:
    from infrastructure.db.models import Base, PG_VIEWS

    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
