from application.alert.commands.delete_alert import DeleteAlertCommand
from domain.alert.entities import AlertEntity
from domain.alert.repository import AlertRepository
from shared.exceptions import NotFoundException


class DeleteAlertHandler:
    def __init__(self, alert_repository: AlertRepository):
        self.alert_repository = alert_repository

    def handle(self, command: DeleteAlertCommand) -> AlertEntity:
        alert = self.alert_repository.delete(command.alert_id)
        if not alert:
            raise NotFoundException("Alert not found")
        return alert
