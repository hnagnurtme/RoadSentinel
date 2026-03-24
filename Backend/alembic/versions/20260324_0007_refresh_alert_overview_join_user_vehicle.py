"""refresh alert overview join user and vehicle

Revision ID: 20260324_0007
Revises: 20260324_0006
Create Date: 2026-03-24 23:30:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from infrastructure.db.models import PG_VIEWS


# revision identifiers, used by Alembic.
revision: str = "20260324_0007"
down_revision: Union[str, Sequence[str], None] = "20260324_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))


def downgrade() -> None:
    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))
