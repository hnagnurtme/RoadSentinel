import { ApiEnvelope, requestJson } from "@/api/http";
import { env } from "@/config/env";
import { Appeal, AppealApiDto, AppealStatus, mapAppealApiDto } from "@/types/appeal";

interface CreateAppealPayload {
  alertId: string;
  description?: string;
  attachmentUrl?: string;
}

interface ReviewAppealPayload {
  status: Exclude<AppealStatus, "PENDING">;
  adminNote?: string;
}

export async function createAppeal(payload: CreateAppealPayload): Promise<Appeal> {
  const response = await requestJson<ApiEnvelope<AppealApiDto>>(`${env.apiBaseUrl}/appeals`, {
    method: "POST",
    body: JSON.stringify({
      alert_id: payload.alertId,
      description: payload.description || undefined,
      attachment_url: payload.attachmentUrl || undefined,
    }),
  });
  return mapAppealApiDto(response.data);
}

export async function listMyAppeals(): Promise<Appeal[]> {
  const response = await requestJson<ApiEnvelope<AppealApiDto[]>>(`${env.apiBaseUrl}/appeals/my`, {
    method: "GET",
  });
  return response.data.map(mapAppealApiDto);
}

export async function listAppealsAdmin(): Promise<Appeal[]> {
  const response = await requestJson<ApiEnvelope<AppealApiDto[]>>(`${env.apiBaseUrl}/appeals`, {
    method: "GET",
  });
  return response.data.map(mapAppealApiDto);
}

export async function reviewAppeal(appealId: string, payload: ReviewAppealPayload): Promise<Appeal> {
  const response = await requestJson<ApiEnvelope<AppealApiDto>>(
    `${env.apiBaseUrl}/appeals/${appealId}/review`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status: payload.status,
        admin_note: payload.adminNote || undefined,
      }),
    },
  );
  return mapAppealApiDto(response.data);
}
