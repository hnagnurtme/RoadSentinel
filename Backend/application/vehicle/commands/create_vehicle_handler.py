from application.vehicle.commands.create_vehicle import CreateVehicleCommand
from domain.vehicle.entities import VehicleEntity
from domain.vehicle.repository import VehicleRepository
from domain.vehicle.services import VehicleDomainService


class CreateVehicleHandler:
    def __init__(self, vehicle_repository: VehicleRepository):
        self.vehicle_repository = vehicle_repository
        self.domain_service = VehicleDomainService(vehicle_repository)

    def handle(self, command: CreateVehicleCommand) -> VehicleEntity:
        self.domain_service.validate_new_vehicle(
            plate_number=command.plate_number,
            production_year=command.production_year,
        )

        vehicle = VehicleEntity(
            plate_number=command.plate_number.strip().upper(),
            manufacturer=command.manufacturer,
            model=command.model,
            vehicle_image_url=command.vehicle_image_url,
            color=command.color,
            production_year=command.production_year,
            vin=command.vin,
        )
        return self.vehicle_repository.create(vehicle)
