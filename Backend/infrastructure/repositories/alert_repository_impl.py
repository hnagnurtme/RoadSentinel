from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from domain.alert.entities import AlertEntity
from domain.alert.repository import AlertRepository
from domain.alert.value_objects import AlertType as DomainAlertType
from infrastructure.db.models import Alert
from infrastructure.db.models.alert.tables import AlertType as DbAlertType


class AlertRepositoryImpl(AlertRepository):
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_entity(row: Alert) -> AlertEntity:
        return AlertEntity(
            _id=row._id,
            message=row.message,
            alert_type=DomainAlertType(row.alert_type.value),
            device_id=row.device_id,
            driver_id=row.driver_id,
            vehicle_id=row.vehicle_id,
            evidence_url=row.evidence_url,
            latitude=row.latitude,
            longitude=row.longitude,
            _created_at=row._created_at,
            _updated_at=row._updated_at,
            _deleted_at=row._deleted_at,
        )

    def create(self, alert: AlertEntity) -> AlertEntity:
        row = Alert(
            message=alert.message,
            alert_type=DbAlertType(alert.alert_type.value),
            device_id=alert.device_id,
            driver_id=alert.driver_id,
            vehicle_id=alert.vehicle_id,
            evidence_url=alert.evidence_url,
            latitude=alert.latitude,
            longitude=alert.longitude,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_entity(row)

    def get_by_id(self, alert_id: uuid.UUID) -> AlertEntity | None:
        stmt = select(Alert).where(Alert._id == alert_id, Alert._deleted_at.is_(None))
        row = self.db.execute(stmt).scalar_one_or_none()
        if not row:
            return None
        return self._to_entity(row)

    def list(
        self, limit: int = 20, driver_id: uuid.UUID | None = None
    ) -> list[AlertEntity]:
        stmt = (
            select(Alert)
            .where(Alert._deleted_at.is_(None))
            .order_by(Alert._created_at.desc())
            .limit(limit)
        )
        if driver_id is not None:
            stmt = stmt.where(Alert.driver_id == driver_id)

        rows = self.db.execute(stmt).scalars().all()
        return [self._to_entity(row) for row in rows]

    def delete(self, alert_id: uuid.UUID) -> AlertEntity | None:
        stmt = select(Alert).where(Alert._id == alert_id, Alert._deleted_at.is_(None))
        row = self.db.execute(stmt).scalar_one_or_none()
        if not row:
            return None

        row._deleted_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_entity(row)
