"""move users table to user schema and rename to user

Revision ID: 20260324_0002
Revises: 20260323_0001
Create Date: 2026-03-24 00:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260324_0002"
down_revision = "20260323_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    schema_name = "user"

    if schema_name not in inspector.get_schema_names():
        op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "user"'))

    public_tables = set(inspector.get_table_names(schema="public"))
    user_tables = set(inspector.get_table_names(schema=schema_name))

    if "users" in public_tables:
        # Move public.users only when target table does not already exist.
        if "user" not in user_tables:
            op.execute(sa.text('ALTER TABLE public.users SET SCHEMA "user"'))

    user_tables = set(sa.inspect(bind).get_table_names(schema=schema_name))

    if "users" in user_tables and "user" not in user_tables:
        op.execute(sa.text('ALTER TABLE "user".users RENAME TO "user"'))
    elif "user" not in user_tables:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            schema=schema_name,
        )
        op.create_index(
            "ix_user_id",
            "user",
            ["id"],
            unique=False,
            schema=schema_name,
        )
        op.create_index(
            "ix_user_email",
            "user",
            ["email"],
            unique=True,
            schema=schema_name,
        )

    # Normalize legacy index names after table move/rename.
    user_indexes = {
        idx["name"] for idx in sa.inspect(bind).get_indexes("user", schema=schema_name)
    }
    if "ix_users_id" in user_indexes and "ix_user_id" not in user_indexes:
        op.execute(sa.text('ALTER INDEX "user".ix_users_id RENAME TO ix_user_id'))
    if "ix_users_email" in user_indexes and "ix_user_email" not in user_indexes:
        op.execute(sa.text('ALTER INDEX "user".ix_users_email RENAME TO ix_user_email'))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    schema_name = "user"
    if schema_name not in inspector.get_schema_names():
        return

    user_tables = set(inspector.get_table_names(schema=schema_name))

    if "user" in user_tables and "users" not in user_tables:
        op.execute(sa.text('ALTER TABLE "user"."user" RENAME TO users'))

    user_indexes = (
        {
            idx["name"]
            for idx in sa.inspect(bind).get_indexes("users", schema=schema_name)
        }
        if "users" in sa.inspect(bind).get_table_names(schema=schema_name)
        else set()
    )
    if "ix_user_id" in user_indexes and "ix_users_id" not in user_indexes:
        op.execute(sa.text('ALTER INDEX "user".ix_user_id RENAME TO ix_users_id'))
    if "ix_user_email" in user_indexes and "ix_users_email" not in user_indexes:
        op.execute(sa.text('ALTER INDEX "user".ix_user_email RENAME TO ix_users_email'))

    user_tables = set(sa.inspect(bind).get_table_names(schema=schema_name))
    if "users" in user_tables:
        op.execute(sa.text('ALTER TABLE "user".users SET SCHEMA public'))

    remaining = set(sa.inspect(bind).get_table_names(schema=schema_name))
    if not remaining:
        op.execute(sa.text('DROP SCHEMA IF EXISTS "user"'))
