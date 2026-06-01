import { env } from "@/config/env";
import { Alert, AlertApiDto, mapAlertApiDto } from "@/types/alert";
import { ApiEnvelope, requestJson } from "@/api/http";

function normalizeAlertPayload(data: AlertApiDto[] | AlertApiDto): AlertApiDto[] {
  return Array.isArray(data) ? data : [data];
}

export async function listAlerts(
  limit = 20,
  driverId?: string,
  vehicleId?: string,
  startDate?: string,
  endDate?: string
): Promise<Alert[]> {
  const query = new URLSearchParams({ limit: String(limit) });

  if (driverId) {
    query.set("driver_id", driverId);
  }

  if (vehicleId) {
    query.set("vehicle_id", vehicleId);
  }

  if (startDate) {
    query.set("start_date", startDate);
  }

  if (endDate) {
    query.set("end_date", endDate);
  }

  const url = `${env.apiBaseUrl}/alerts?${query.toString()}`;
  const response = await requestJson<ApiEnvelope<AlertApiDto[] | AlertApiDto>>(url, { method: "GET" });

  return normalizeAlertPayload(response.data).map(mapAlertApiDto);
}

export async function getAlert(alertId: string): Promise<Alert> {
  const url = `${env.apiBaseUrl}/alerts/${alertId}`;
  const response = await requestJson<ApiEnvelope<AlertApiDto>>(url, { method: "GET" });
  return mapAlertApiDto(response.data);
}

export async function deleteAlert(alertId: string): Promise<Alert> {
  const url = `${env.apiBaseUrl}/alerts/${alertId}`;
  const response = await requestJson<ApiEnvelope<AlertApiDto>>(url, { method: "DELETE" });
  return mapAlertApiDto(response.data);
}
