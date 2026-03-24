from infrastructure.db.models.base import PGView


class AlertOverviewView(PGView):
    schema = "alert"
    name = "_alert_overview"
    query = """
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
        length(a.message) AS message_length,
        a._created_at,
        a._updated_at,
        a._deleted_at
    FROM "alert".alert a
    """
