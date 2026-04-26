"""
application/alert/queries/list_alerts_overview_handler.py
----------------------------------------------------
Handler for listing alerts with pre-joined user and vehicle data using AlertOverviewView.
"""

from __future__ import annotations

import uuid
from typing import Any, NamedTuple

from application.alert.queries.list_alerts_overview import ListAlertsOverviewQuery
from infrastructure.db.session import SessionLocal


class AlertOverviewRow(NamedTuple):
    """Raw row from AlertOverviewView."""

    _id: uuid.UUID
    message: str
    alert_type: str
    evidence_url: str | None
    device_id: uuid.UUID
    driver_id: uuid.UUID | None
    vehicle_id: uuid.UUID | None
    latitude: float | None
    longitude: float | None
    # User fields
    user__id: uuid.UUID | None
    user__email: str | None
    user__name: str | None
    user__avatar_image_url: str | None
    user__name__family: str | None
    user__name__given: str | None
    user__name__middle: str | None
    user__name__prefix: str | None
    user__name__suffix: str | None
    user__birthday: str | None
    user__gender: str | None
    user__address__city: str | None
    user__address__country: str | None
    user__address__line1: str | None
    user__address__line2: str | None
    user___created_at: str | None
    user___updated_at: str | None
    user___deleted_at: str | None
    # Vehicle fields
    vehicle__id: uuid.UUID | None
    vehicle__plate_number: str | None
    vehicle__manufacturer: str | None
    vehicle__model: str | None
    vehicle__vehicle_image_url: str | None
    vehicle__color: str | None
    vehicle__production_year: int | None
    vehicle__vin: str | None
    vehicle___created_at: str | None
    vehicle___updated_at: str | None
    vehicle___deleted_at: str | None
    message_length: int
    _created_at: str
    _updated_at: str
    _deleted_at: str | None


class ListAlertsOverviewHandler:
    """Handle ListAlertsOverviewQuery using AlertOverviewView to eliminate N+1 queries."""

    def handle(self, query: ListAlertsOverviewQuery) -> list[dict[str, Any]]:
        """Execute query against AlertOverviewView and return formatted results."""
        limit = max(1, min(query.limit, 100))

        with SessionLocal() as db:
            # Build the base query
            sql = """
            SELECT * FROM alert."_alert_overview"
            WHERE "_deleted_at" IS NULL
            """
            params = {}

            # Add driver_id filter if provided
            if query.driver_id is not None:
                sql += " AND driver_id = :driver_id"
                params["driver_id"] = str(query.driver_id)

            # Add ordering and limit
            sql += ' ORDER BY "_created_at" DESC LIMIT :limit'
            params["limit"] = limit

            # Execute query
            result = db.execute(sql, params)
            rows = result.fetchall()

            # Convert rows to dictionaries with proper nested structure
            alerts = []
            for row in rows:
                alert_dict = {
                    "_id": str(row._id),
                    "message": row.message,
                    "alert_type": row.alert_type,
                    "evidence_url": row.evidence_url,
                    "device_id": str(row.device_id),
                    "driver_id": str(row.driver_id) if row.driver_id else None,
                    "vehicle_id": str(row.vehicle_id) if row.vehicle_id else None,
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "_created_at": row._created_at,
                    "_updated_at": row._updated_at,
                    "_deleted_at": row._deleted_at,
                    "message_length": row.message_length,
                }

                # Add user data if present
                if row.user__id is not None:
                    alert_dict["user"] = {
                        "_id": str(row.user__id),
                        "email": row.user__email,
                        "name": row.user__name,
                        "avatar_image_url": row.user__avatar_image_url,
                        "name__family": row.user__name__family,
                        "name__given": row.user__name__given,
                        "name__middle": row.user__name__middle,
                        "name__prefix": row.user__name__prefix,
                        "name__suffix": row.user__name__suffix,
                        "birthday": row.user__birthday,
                        "gender": row.user__gender,
                        "address__city": row.user__address__city,
                        "address__country": row.user__address__country,
                        "address__line1": row.user__address__line1,
                        "address__line2": row.user__address__line2,
                        "_created_at": row.user___created_at,
                        "_updated_at": row.user___updated_at,
                        "_deleted_at": row.user___deleted_at,
                    }
                else:
                    alert_dict["user"] = None

                # Add vehicle data if present
                if row.vehicle__id is not None:
                    alert_dict["vehicle"] = {
                        "_id": str(row.vehicle__id),
                        "plate_number": row.vehicle__plate_number,
                        "manufacturer": row.vehicle__manufacturer,
                        "model": row.vehicle__model,
                        "vehicle_image_url": row.vehicle__vehicle_image_url,
                        "color": row.vehicle__color,
                        "production_year": row.vehicle__production_year,
                        "vin": row.vehicle__vin,
                        "_created_at": row.vehicle___created_at,
                        "_updated_at": row.vehicle___updated_at,
                        "_deleted_at": row.vehicle___deleted_at,
                    }
                else:
                    alert_dict["vehicle"] = None

                alerts.append(alert_dict)

            return alerts
