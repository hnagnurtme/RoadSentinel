from application.alert.commands.create_alert import CreateAlertCommand
from domain.alert.entities import AlertEntity
from domain.alert.repository import AlertRepository
from domain.alert.services import AlertDomainService


class CreateAlertHandler:
    def __init__(self, alert_repository: AlertRepository):
        self.alert_repository = alert_repository
        self.domain_service = AlertDomainService()

    def handle(self, command: CreateAlertCommand) -> AlertEntity:
        alert = AlertEntity(
            message=command.message,
            alert_type=command.alert_type,
            device_id=command.device_id,
            driver_id=command.driver_id,
            vehicle_id=command.vehicle_id,
            evidence_url=command.evidence_url,
            latitude=command.latitude,
            longitude=command.longitude,
        )
        self.domain_service.validate_new_alert(alert)
        return self.alert_repository.create(alert)
