from domain.vehicle.repository import VehicleRepository
from shared.exceptions import ConflictException, ValidationException


class VehicleDomainService:
    def __init__(self, vehicle_repository: VehicleRepository):
        self.vehicle_repository = vehicle_repository

    def validate_new_vehicle(
        self, plate_number: str, production_year: int | None
    ) -> None:
        normalized_plate = plate_number.strip().upper()
        if not normalized_plate:
            raise ValidationException("plate_number is required")

        if production_year is not None and not (1900 <= production_year <= 2100):
            raise ValidationException("production_year must be between 1900 and 2100")

        existing = self.vehicle_repository.get_by_plate_number(normalized_plate)
        if existing:
            raise ConflictException("plate_number already exists")
