import { env } from "@/config/env";
import { Alert, AlertApiDto, mapAlertApiDto } from "@/types/alert";
import { ApiEnvelope, requestJson } from "@/api/http";

function normalizeAlertPayload(data: AlertApiDto[] | AlertApiDto): AlertApiDto[] {
  return Array.isArray(data) ? data : [data];
}

export async function listAlerts(limit = 20, driverId?: string): Promise<Alert[]> {
  const query = new URLSearchParams({ limit: String(limit) });

  if (driverId) {
    query.set("driver_id", driverId);
  }

  const url = `${env.apiBaseUrl}/alerts?${query.toString()}`;
  const response = await requestJson<ApiEnvelope<AlertApiDto[] | AlertApiDto>>(url, { method: "GET" });

  return normalizeAlertPayload(response.data).map(mapAlertApiDto);
}
