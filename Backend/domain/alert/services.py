from domain.alert.entities import AlertEntity
from domain.alert.value_objects import Position
from shared.exceptions import ValidationException


class AlertDomainService:
    def validate_new_alert(self, alert: AlertEntity) -> None:
        if not alert.message or not alert.message.strip():
            raise ValidationException("Alert message is required")
        Position(latitude=alert.latitude, longitude=alert.longitude)
