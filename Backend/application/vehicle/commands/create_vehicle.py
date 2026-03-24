from dataclasses import dataclass


@dataclass(frozen=True)
class CreateVehicleCommand:
    plate_number: str
    manufacturer: str | None = None
    model: str | None = None
    color: str | None = None
    production_year: int | None = None
    vin: str | None = None
