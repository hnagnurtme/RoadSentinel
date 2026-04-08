from abc import ABC, abstractmethod
import uuid

from domain.alert.entities import AlertEntity


class AlertRepository(ABC):
    @abstractmethod
    def create(self, alert: AlertEntity) -> AlertEntity:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, alert_id: uuid.UUID) -> AlertEntity | None:
        raise NotImplementedError

    @abstractmethod
    def list(
        self, limit: int = 20, driver_id: uuid.UUID | None = None
    ) -> list[AlertEntity]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, alert_id: uuid.UUID) -> AlertEntity | None:
        raise NotImplementedError
