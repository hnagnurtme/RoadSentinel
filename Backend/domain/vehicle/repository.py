from abc import ABC, abstractmethod
import uuid

from domain.vehicle.entities import VehicleEntity


class VehicleRepository(ABC):
    @abstractmethod
    def create(self, vehicle: VehicleEntity) -> VehicleEntity:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, vehicle_id: uuid.UUID) -> VehicleEntity | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_plate_number(self, plate_number: str) -> VehicleEntity | None:
        raise NotImplementedError

    @abstractmethod
    def list(self, limit: int = 20) -> list[VehicleEntity]:
        raise NotImplementedError
