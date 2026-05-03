"""add appeal table

Revision ID: 9a1d8b3f6c21
Revises: f8c2_user_auth_view
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "9a1d8b3f6c21"
down_revision = "f8c2_user_auth_view"
branch_labels = None
depends_on = None


def upgrade() -> None:
    appeal_status = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "REJECTED",
        name="appeal_status_enum",
        schema="alert",
        create_type=False,
    )
    appeal_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "appeal",
        sa.Column(
            "_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", appeal_status, nullable=False, server_default="PENDING"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.String(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("_id"),
        schema="alert",
    )
    op.create_index("ix_alert_appeal_alert_id", "appeal", ["alert_id"], schema="alert")
    op.create_index(
        "ix_alert_appeal_driver_id", "appeal", ["driver_id"], schema="alert"
    )
    op.create_index("ix_alert_appeal_status", "appeal", ["status"], schema="alert")


def downgrade() -> None:
    op.drop_index("ix_alert_appeal_status", table_name="appeal", schema="alert")
    op.drop_index("ix_alert_appeal_driver_id", table_name="appeal", schema="alert")
    op.drop_index("ix_alert_appeal_alert_id", table_name="appeal", schema="alert")
    op.drop_table("appeal", schema="alert")

    appeal_status = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "REJECTED",
        name="appeal_status_enum",
        schema="alert",
    )
    appeal_status.drop(op.get_bind(), checkfirst=True)
