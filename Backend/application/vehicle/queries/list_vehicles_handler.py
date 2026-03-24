from application.vehicle.queries.list_vehicles import ListVehiclesQuery
from domain.vehicle.entities import VehicleEntity
from domain.vehicle.repository import VehicleRepository


class ListVehiclesHandler:
    def __init__(self, vehicle_repository: VehicleRepository):
        self.vehicle_repository = vehicle_repository

    def handle(self, query: ListVehiclesQuery) -> list[VehicleEntity]:
        limit = max(1, min(query.limit, 100))
        return self.vehicle_repository.list(limit=limit)
