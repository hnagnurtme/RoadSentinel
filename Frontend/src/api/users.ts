import { requestJson, ApiEnvelope } from "./http";
import { env } from "@/config/env";

export interface User {
  id: string;
  email: string;
  name?: string;
  role: string;
  fingerprint_id?: string;
  [key: string]: any;
}

export interface DrivingSession {
  id: string;
  status: string;
  started_at: string;
  ended_at: string | null;
}

export async function getUsers(): Promise<User[]> {
  const { data } = await requestJson<ApiEnvelope<any[]>>(`${env.apiBaseUrl}/users`);
  return data.map((u) => ({
    ...u,
    id: u._id,
  }));
}

export async function createUser(payload: Partial<User> & { email: string; name?: string; password?: string }): Promise<User> {
  const { data } = await requestJson<ApiEnvelope<any>>(`${env.apiBaseUrl}/users`, {
    method: "POST",
    body: JSON.stringify({ ...payload, role: "driver" }),
  });
  return { ...data, id: data._id };
}

export async function updateUser(userId: string, payload: Partial<User>): Promise<void> {
  await requestJson(`${env.apiBaseUrl}/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function updateFingerprint(userId: string, fingerprintId: string): Promise<void> {
  await requestJson(`${env.apiBaseUrl}/users/${userId}/fingerprint`, {
    method: "PATCH",
    body: JSON.stringify({ fingerprint_id: fingerprintId })
  });
}

export async function getDrivingSessions(userId: string): Promise<DrivingSession[]> {
  const { data } = await requestJson<ApiEnvelope<DrivingSession[]>>(`${env.apiBaseUrl}/users/${userId}/driving-sessions`);
  return data;
}

export async function enrollFingerprint(userId: string): Promise<void> {
  await requestJson(`${env.apiBaseUrl}/users/${userId}/enroll`, {
    method: "POST",
  });
}
