from fastapi import APIRouter, Depends, Query
import uuid

from application.vehicle.commands.create_vehicle import CreateVehicleCommand
from application.vehicle.commands.create_vehicle_handler import CreateVehicleHandler
from application.vehicle.queries.get_vehicle import GetVehicleQuery
from application.vehicle.queries.get_vehicle_handler import GetVehicleHandler
from application.vehicle.queries.list_vehicles import ListVehiclesQuery
from application.vehicle.queries.list_vehicles_handler import ListVehiclesHandler
from application.vehicle.vehicle_dto import CreateVehicleRequest, VehicleResponse
from interfaces.api.deps import (
    get_create_vehicle_handler,
    get_get_vehicle_handler,
    get_list_vehicles_handler,
)
from interfaces.api.response import success_response

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _to_vehicle_response(vehicle) -> VehicleResponse:
    return VehicleResponse(
        id=vehicle._id,
        plate_number=vehicle.plate_number,
        manufacturer=vehicle.manufacturer,
        model=vehicle.model,
        color=vehicle.color,
        production_year=vehicle.production_year,
        vin=vehicle.vin,
        created_at=vehicle._created_at,
        updated_at=vehicle._updated_at,
        deleted_at=vehicle._deleted_at,
    )


@router.post("")
def create_vehicle(
    payload: CreateVehicleRequest,
    handler: CreateVehicleHandler = Depends(get_create_vehicle_handler),
):
    vehicle = handler.handle(
        CreateVehicleCommand(
            plate_number=payload.plate_number,
            manufacturer=payload.manufacturer,
            model=payload.model,
            color=payload.color,
            production_year=payload.production_year,
            vin=payload.vin,
        )
    )
    return success_response(
        data=_to_vehicle_response(vehicle).model_dump(by_alias=True)
    )


@router.get("/{vehicle_id}")
def get_vehicle(
    vehicle_id: uuid.UUID,
    handler: GetVehicleHandler = Depends(get_get_vehicle_handler),
):
    vehicle = handler.handle(GetVehicleQuery(vehicle_id=vehicle_id))
    return success_response(
        data=_to_vehicle_response(vehicle).model_dump(by_alias=True)
    )


@router.get("")
def list_vehicles(
    limit: int = Query(default=20, ge=1, le=100),
    handler: ListVehiclesHandler = Depends(get_list_vehicles_handler),
):
    vehicles = handler.handle(ListVehiclesQuery(limit=limit))
    return success_response(
        data=[
            _to_vehicle_response(vehicle).model_dump(by_alias=True)
            for vehicle in vehicles
        ]
    )
