"""
application/alert/queries/list_alerts_overview_handler.py
----------------------------------------------------
Handler for listing alerts with pre-joined user and vehicle data using AlertOverviewView.
"""

from __future__ import annotations

from typing import Any

from application.alert.queries.list_alerts_overview import ListAlertsOverviewQuery
from infrastructure.db.session import SessionLocal
from sqlalchemy import text




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
            result = db.execute(text(sql), params)
            rows = result.fetchall()

            # Convert rows to dictionaries with proper nested structure
            alerts = []
            for row in rows:
                # Access row data using attribute-style access
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
                user_id = getattr(row, 'user__id', None)
                if user_id is not None:
                    alert_dict["user"] = {
                        "_id": str(user_id),
                        "email": getattr(row, 'user__email', None),
                        "name": getattr(row, 'user__name', None),
                        "avatar_image_url": getattr(row, 'user__avatar_image_url', None),
                        "name__family": getattr(row, 'user__name__family', None),
                        "name__given": getattr(row, 'user__name__given', None),
                        "name__middle": getattr(row, 'user__name__middle', None),
                        "name__prefix": getattr(row, 'user__name__prefix', None),
                        "name__suffix": getattr(row, 'user__name__suffix', None),
                        "birthday": getattr(row, 'user__birthday', None),
                        "gender": getattr(row, 'user__gender', None),
                        "address__city": getattr(row, 'user__address__city', None),
                        "address__country": getattr(row, 'user__address__country', None),
                        "address__line1": getattr(row, 'user__address__line1', None),
                        "address__line2": getattr(row, 'user__address__line2', None),
                        "_created_at": getattr(row, 'user__created_at', None),
                        "_updated_at": getattr(row, 'user__updated_at', None),
                        "_deleted_at": getattr(row, 'user__deleted_at', None),
                    }
                else:
                    alert_dict["user"] = None

                # Add vehicle data if present
                vehicle_id = getattr(row, 'vehicle__id', None)
                if vehicle_id is not None:
                    alert_dict["vehicle"] = {
                        "_id": str(vehicle_id),
                        "plate_number": getattr(row, 'vehicle__plate_number', None),
                        "manufacturer": getattr(row, 'vehicle__manufacturer', None),
                        "model": getattr(row, 'vehicle__model', None),
                        "vehicle_image_url": getattr(row, 'vehicle__vehicle_image_url', None),
                        "color": getattr(row, 'vehicle__color', None),
                        "production_year": getattr(row, 'vehicle__production_year', None),
                        "vin": getattr(row, 'vehicle__vin', None),
                        "_created_at": getattr(row, 'vehicle__created_at', None),
                        "_updated_at": getattr(row, 'vehicle__updated_at', None),
                        "_deleted_at": getattr(row, 'vehicle__deleted_at', None),
                    }
                else:
                    alert_dict["vehicle"] = None

                alerts.append(alert_dict)

            return alerts
