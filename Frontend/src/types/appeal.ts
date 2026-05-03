export type AppealStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface AppealApiDto {
  _id: string;
  alert_id: string;
  driver_id: string;
  status: AppealStatus;
  description: string | null;
  attachment_url: string | null;
  admin_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  _created_at: string | null;
  _updated_at: string | null;
}

export interface Appeal {
  id: string;
  alertId: string;
  driverId: string;
  status: AppealStatus;
  description: string | null;
  attachmentUrl: string | null;
  adminNote: string | null;
  reviewedBy: string | null;
  reviewedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export function mapAppealApiDto(dto: AppealApiDto): Appeal {
  return {
    id: dto._id,
    alertId: dto.alert_id,
    driverId: dto.driver_id,
    status: dto.status,
    description: dto.description,
    attachmentUrl: dto.attachment_url,
    adminNote: dto.admin_note,
    reviewedBy: dto.reviewed_by,
    reviewedAt: dto.reviewed_at,
    createdAt: dto._created_at,
    updatedAt: dto._updated_at,
  };
}
