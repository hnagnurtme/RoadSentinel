from sqlalchemy import select
from sqlalchemy.orm import Session
import uuid

from domain.vehicle.entities import VehicleEntity
from domain.vehicle.repository import VehicleRepository
from infrastructure.db.models import Vehicle


class VehicleRepositoryImpl(VehicleRepository):
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_entity(row: Vehicle) -> VehicleEntity:
        return VehicleEntity(
            _id=row._id,
            plate_number=row.plate_number,
            manufacturer=row.manufacturer,
            model=row.model,
            vehicle_image_url=row.vehicle_image_url,
            color=row.color,
            production_year=row.production_year,
            vin=row.vin,
            device_id=row.device_id,
            _created_at=row._created_at,
            _updated_at=row._updated_at,
            _deleted_at=row._deleted_at,
        )

    def create(self, vehicle: VehicleEntity) -> VehicleEntity:
        row = Vehicle(
            plate_number=vehicle.plate_number,
            manufacturer=vehicle.manufacturer,
            model=vehicle.model,
            vehicle_image_url=vehicle.vehicle_image_url,
            color=vehicle.color,
            production_year=vehicle.production_year,
            vin=vehicle.vin,
            device_id=vehicle.device_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_entity(row)

    def get_by_id(self, vehicle_id: uuid.UUID) -> VehicleEntity | None:
        stmt = select(Vehicle).where(Vehicle._id == vehicle_id)
        row = self.db.execute(stmt).scalar_one_or_none()
        if not row:
            return None
        return self._to_entity(row)

    def get_by_plate_number(self, plate_number: str) -> VehicleEntity | None:
        stmt = select(Vehicle).where(Vehicle.plate_number == plate_number)
        row = self.db.execute(stmt).scalar_one_or_none()
        if not row:
            return None
        return self._to_entity(row)

    def list(self, limit: int = 20) -> list[VehicleEntity]:
        stmt = select(Vehicle).order_by(Vehicle._created_at.desc()).limit(limit)
        rows = self.db.execute(stmt).scalars().all()
        return [self._to_entity(row) for row in rows]
