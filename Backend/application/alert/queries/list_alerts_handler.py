from application.alert.queries.list_alerts import ListAlertsQuery
from domain.alert.entities import AlertEntity
from domain.alert.repository import AlertRepository


class ListAlertsHandler:
    def __init__(self, alert_repository: AlertRepository):
        self.alert_repository = alert_repository

    def handle(self, query: ListAlertsQuery) -> list[AlertEntity]:
        limit = max(1, min(query.limit, 100))
        return self.alert_repository.list(limit=limit, driver_id=query.driver_id)
