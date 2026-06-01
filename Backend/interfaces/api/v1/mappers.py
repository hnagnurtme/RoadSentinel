"""
interfaces/api/v1/mappers.py
-----------------------------
Shared mappers from domain entities to Pydantic response DTOs.

Previously, ``_to_user_response()`` was duplicated in both ``user.py`` and
``alert.py``.  Centralising them here ensures consistency and eliminates the
DRY violation.
"""
from __future__ import annotations

from application.alert.alert_dto import AlertResponse
from application.user.user_dto import UserResponse
from application.vehicle.vehicle_dto import VehicleResponse


def to_user_response(user) -> UserResponse:
    """Map a ``UserEntity`` to a ``UserResponse`` DTO."""
    return UserResponse(
        id=user._id,
        email=user.email.value,
        name=user.name,
        avatar_image_url=user.avatar_image_url,
        name__family=user.name__family,
        name__given=user.name__given,
        name__middle=user.name__middle,
        name__prefix=user.name__prefix,
        name__suffix=user.name__suffix,
        birthday=user.birthday,
        gender=user.gender,
        address__city=user.address__city,
        address__country=user.address__country,
        address__line1=user.address__line1,
        address__line2=user.address__line2,
        created_at=user.created_at,
        updated_at=user.updated_at,
        deleted_at=user.deleted_at,
        role=user.role,
        fingerprint_id=getattr(user, "fingerprint_id", None),
    )


def to_vehicle_response(vehicle) -> VehicleResponse:
    """Map a ``VehicleEntity`` to a ``VehicleResponse`` DTO."""
    return VehicleResponse(
        id=vehicle._id,
        plate_number=vehicle.plate_number,
        manufacturer=vehicle.manufacturer,
        model=vehicle.model,
        vehicle_image_url=vehicle.vehicle_image_url,
        color=vehicle.color,
        production_year=vehicle.production_year,
        vin=vehicle.vin,
        device_id=vehicle.device_id,
        created_at=vehicle._created_at,
        updated_at=vehicle._updated_at,
        deleted_at=vehicle._deleted_at,
    )


def to_alert_response(
    alert,
    user: UserResponse | None = None,
    vehicle: VehicleResponse | None = None,
) -> AlertResponse:
    """Map an ``AlertEntity`` to an ``AlertResponse`` DTO."""
    return AlertResponse(
        id=alert._id,
        message=alert.message,
        alert_type=alert.alert_type,
        device_id=alert.device_id,
        driver_id=alert.driver_id,
        vehicle_id=alert.vehicle_id,
        evidence_url=alert.evidence_url,
        latitude=alert.latitude,
        longitude=alert.longitude,
        user=user,
        vehicle=vehicle,
        created_at=alert._created_at,
        updated_at=alert._updated_at,
        deleted_at=alert._deleted_at,
    )
