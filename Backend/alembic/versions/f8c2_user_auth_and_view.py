"""user password_hash, role + alert overview user__role

Revision ID: f8c2_user_auth_view
Revises: 22d72a301c78
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

from infrastructure.db.models.alert.views import AlertOverviewView

revision = "f8c2_user_auth_view"
down_revision = "22d72a301c78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("password_hash", sa.String(), nullable=True),
        schema="user",
    )
    op.add_column(
        "user",
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default="driver",
        ),
        schema="user",
    )

    op.execute(sa.text('DROP VIEW IF EXISTS alert."_alert_overview"'))
    op.execute(
        sa.text(f'CREATE VIEW alert."_alert_overview" AS {AlertOverviewView.query}')
    )


def downgrade() -> None:
    op.execute(sa.text('DROP VIEW IF EXISTS alert."_alert_overview"'))

    _legacy_overview = """
    SELECT
        a._id,
        a.message,
        a.alert_type,
        a.evidence_url,
        a.device_id,
        a.driver_id,
        a.vehicle_id,
        a.latitude,
        a.longitude,
        u._id AS user__id,
        u.email AS user__email,
        u.name AS user__name,
        u.avatar_image_url AS user__avatar_image_url,
        u.name__family AS user__name__family,
        u.name__given AS user__name__given,
        u.name__middle AS user__name__middle,
        u.name__prefix AS user__name__prefix,
        u.name__suffix AS user__name__suffix,
        u.birthday AS user__birthday,
        u.gender AS user__gender,
        u.address__city AS user__address__city,
        u.address__country AS user__address__country,
        u.address__line1 AS user__address__line1,
        u.address__line2 AS user__address__line2,
        u._created_at AS user__created_at,
        u._updated_at AS user__updated_at,
        u._deleted_at AS user__deleted_at,
        v._id AS vehicle__id,
        v.plate_number AS vehicle__plate_number,
        v.manufacturer AS vehicle__manufacturer,
        v.model AS vehicle__model,
        v.vehicle_image_url AS vehicle__vehicle_image_url,
        v.color AS vehicle__color,
        v.production_year AS vehicle__production_year,
        v.vin AS vehicle__vin,
        v._created_at AS vehicle__created_at,
        v._updated_at AS vehicle__updated_at,
        v._deleted_at AS vehicle__deleted_at,
        length(a.message) AS message_length,
        a._created_at,
        a._updated_at,
        a._deleted_at
    FROM "alert".alert a
    LEFT JOIN "user"."user" u ON u._id = a.driver_id
    LEFT JOIN "vehicle"."vehicle" v ON v._id = a.vehicle_id
    """
    op.execute(sa.text(f'CREATE VIEW alert."_alert_overview" AS {_legacy_overview}'))

    op.drop_column("user", "role", schema="user")
    op.drop_column("user", "password_hash", schema="user")