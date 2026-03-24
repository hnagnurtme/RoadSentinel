from infrastructure.db.models.base import PGView


class AlertOverviewView(PGView):
    schema = "alert"
    name = "_alert_overview"
    query = """
    SELECT
        a.id,
        a.message,
        length(a.message) AS message_length,
        a.created_at,
        a.updated_at,
        a.deleted_at
    FROM "alert".alert a
    """
