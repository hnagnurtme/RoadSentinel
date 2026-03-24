from application.alert.queries.get_alert import GetAlertQuery
from domain.alert.entities import AlertEntity
from domain.alert.repository import AlertRepository
from shared.exceptions import NotFoundException


class GetAlertHandler:
    def __init__(self, alert_repository: AlertRepository):
        self.alert_repository = alert_repository

    def handle(self, query: GetAlertQuery) -> AlertEntity:
        alert = self.alert_repository.get_by_id(query.alert_id)
        if not alert:
            raise NotFoundException("Alert not found")
        return alert
