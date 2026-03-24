from application.vehicle.queries.get_vehicle import GetVehicleQuery
from domain.vehicle.entities import VehicleEntity
from domain.vehicle.repository import VehicleRepository
from shared.exceptions import NotFoundException


class GetVehicleHandler:
    def __init__(self, vehicle_repository: VehicleRepository):
        self.vehicle_repository = vehicle_repository

    def handle(self, query: GetVehicleQuery) -> VehicleEntity:
        vehicle = self.vehicle_repository.get_by_id(query.vehicle_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found")
        return vehicle
