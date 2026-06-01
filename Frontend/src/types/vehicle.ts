export interface VehicleApiDto {
  _id: string;
  plate_number: string;
  manufacturer: string;
  model: string;
  vehicle_image_url: string | null;
  color: string | null;
  production_year: number | null;
  vin: string | null;
  device_id: string | null;
  _created_at: string | null;
  _updated_at: string | null;
}

export interface Vehicle {
  id: string;
  plateNumber: string;
  manufacturer: string;
  model: string;
  vehicleImageUrl: string | null;
  color: string | null;
  productionYear: number | null;
  vin: string | null;
  deviceId: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export function mapVehicleFromApi(dto: VehicleApiDto): Vehicle {
  return {
    id: dto._id,
    plateNumber: dto.plate_number,
    manufacturer: dto.manufacturer,
    model: dto.model,
    vehicleImageUrl: dto.vehicle_image_url,
    color: dto.color,
    productionYear: dto.production_year,
    vin: dto.vin,
    deviceId: dto.device_id || null,
    createdAt: dto._created_at,
    updatedAt: dto._updated_at,
  };
}
