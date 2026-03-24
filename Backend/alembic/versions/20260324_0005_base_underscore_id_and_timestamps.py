"""base underscore id and timestamps

Revision ID: 20260324_0005
Revises: 01070dfa83f8
Create Date: 2026-03-24 22:20:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from infrastructure.db.models import PG_VIEWS


# revision identifiers, used by Alembic.
revision: str = "20260324_0005"
down_revision: Union[str, Sequence[str], None] = "01070dfa83f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_time_columns(schema_name: str, table_name: str) -> None:
    pairs = (
        ("created_at", "_created_at"),
        ("updated_at", "_updated_at"),
        ("deleted_at", "_deleted_at"),
    )
    for old, new in pairs:
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = '{schema_name}'
                          AND table_name = '{table_name}'
                          AND column_name = '{old}'
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = '{schema_name}'
                          AND table_name = '{table_name}'
                          AND column_name = '{new}'
                    ) THEN
                        ALTER TABLE "{schema_name}"."{table_name}" RENAME COLUMN {old} TO {new};
                    END IF;
                END
                $$;
                """
            )
        )


def _rename_id_column(
    schema_name: str, table_name: str, old_index: str, new_index: str, old_pk: str
) -> None:
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))

    op.execute(
        sa.text(
            f'ALTER TABLE "{schema_name}"."{table_name}" ADD COLUMN IF NOT EXISTS _id UUID DEFAULT gen_random_uuid()'
        )
    )
    op.execute(
        sa.text(
            f'UPDATE "{schema_name}"."{table_name}" SET _id = gen_random_uuid() WHERE _id IS NULL'
        )
    )
    op.execute(
        sa.text(
            f'ALTER TABLE "{schema_name}"."{table_name}" ALTER COLUMN _id SET NOT NULL'
        )
    )

    op.execute(
        sa.text(
            f'ALTER TABLE "{schema_name}"."{table_name}" DROP CONSTRAINT IF EXISTS {old_pk}'
        )
    )
    op.execute(sa.text(f'DROP INDEX IF EXISTS "{schema_name}".{old_index}'))
    op.execute(
        sa.text(f'ALTER TABLE "{schema_name}"."{table_name}" DROP COLUMN IF EXISTS id')
    )

    op.execute(
        sa.text(
            f'ALTER TABLE "{schema_name}"."{table_name}" ADD CONSTRAINT {old_pk} PRIMARY KEY (_id)'
        )
    )
    op.execute(
        sa.text(
            f'CREATE INDEX IF NOT EXISTS {new_index} ON "{schema_name}"."{table_name}" (_id)'
        )
    )


def upgrade() -> None:
    for view_def in reversed(PG_VIEWS):
        op.execute(sa.text(view_def.drop_sql()))

    _rename_time_columns("user", "user")
    _rename_time_columns("alert", "alert")

    _rename_id_column(
        schema_name="user",
        table_name="user",
        old_index="ix_user_user_id",
        new_index="ix_user_user__id",
        old_pk="user_pkey",
    )
    _rename_id_column(
        schema_name="alert",
        table_name="alert",
        old_index="ix_alert_alert_id",
        new_index="ix_alert_alert__id",
        old_pk="alert_pkey",
    )

    for view_def in PG_VIEWS:
        op.execute(sa.text(view_def.create_sql()))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for 20260324_0005")
