"""init users table

Revision ID: 20260323_0001
Revises:
Create Date: 2026-03-23 00:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    public_tables = set(inspector.get_table_names(schema="public"))

    if "users" not in public_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    # Keep migration safe on databases where table/indexes already exist.
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_id ON public.users (id)"))
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON public.users (email)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_users_email"))
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_users_id"))
    op.execute(sa.text("DROP TABLE IF EXISTS public.users"))
