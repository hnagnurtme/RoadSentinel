import { ApiEnvelope, requestJson } from "./http";
import { env } from "@/config/env";
import type { Vehicle, VehicleApiDto } from "@/types/vehicle";
import { mapVehicleFromApi } from "@/types/vehicle";

export async function getVehicles(limit = 100): Promise<Vehicle[]> {
  const result = await requestJson<ApiEnvelope<VehicleApiDto[]>>(`${env.apiBaseUrl}/vehicles?limit=${limit}`);
  return result.data.map(mapVehicleFromApi);
}

export interface CreateVehiclePayload {
  plate_number: string;
  manufacturer: string;
  model: string;
  vehicle_image_url?: string;
  color?: string;
  production_year?: number;
  vin?: string;
}

export async function createVehicle(payload: CreateVehiclePayload): Promise<Vehicle> {
  const result = await requestJson<ApiEnvelope<VehicleApiDto>>(`${env.apiBaseUrl}/vehicles`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapVehicleFromApi(result.data);
}
