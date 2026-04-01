export interface AlertApiDto {
  _id: string;
  message: string;
  alert_type: string;
  device_id: string;
  driver_id: string | null;
  vehicle_id: string | null;
  evidence_url: string | null;
  latitude: number | null;
  longitude: number | null;
  user?: AlertUserApiDto | null;
  vehicle?: AlertVehicleApiDto | null;
  _created_at: string | null;
  _updated_at: string | null;
  _deleted_at: string | null;
}

export interface AlertUserApiDto {
  _id: string;
  email: string;
  name: string;
  avatar_image_url: string | null;
}

export interface AlertVehicleApiDto {
  _id: string;
  plate_number: string;
  manufacturer: string;
  model: string;
  vehicle_image_url: string | null;
}

export interface Alert {
  id: string;
  message: string;
  alertType: string;
  deviceId: string;
  driverId: string | null;
  vehicleId: string | null;
  evidenceUrl: string | null;
  latitude: number | null;
  longitude: number | null;
  user: AlertUser | null;
  vehicle: AlertVehicle | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface AlertUser {
  id: string;
  email: string;
  name: string;
  avatarImageUrl: string | null;
}

export interface AlertVehicle {
  id: string;
  plateNumber: string;
  manufacturer: string;
  model: string;
  vehicleImageUrl: string | null;
}

export function mapAlertApiDto(dto: AlertApiDto): Alert {
  return {
    id: dto._id,
    message: dto.message,
    alertType: dto.alert_type,
    deviceId: dto.device_id,
    driverId: dto.driver_id,
    vehicleId: dto.vehicle_id,
    evidenceUrl: dto.evidence_url,
    latitude: dto.latitude,
    longitude: dto.longitude,
    user: dto.user
      ? {
          id: dto.user._id,
          email: dto.user.email,
          name: dto.user.name,
          avatarImageUrl: dto.user.avatar_image_url,
        }
      : null,
    vehicle: dto.vehicle
      ? {
          id: dto.vehicle._id,
          plateNumber: dto.vehicle.plate_number,
          manufacturer: dto.vehicle.manufacturer,
          model: dto.vehicle.model,
          vehicleImageUrl: dto.vehicle.vehicle_image_url,
        }
      : null,
    createdAt: dto._created_at,
    updatedAt: dto._updated_at,
  };
}

export function formatAlertTypeLabel(alertType: string): string {
  return alertType
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function getAlertSeverity(alertType: string): "critical" | "moderate" | "advisory" {
  const normalized = alertType.toUpperCase();

  if (["HARD_BRAKE", "COLLISION", "DROWSY", "SLEEPING", "USING_PHONE"].includes(normalized)) {
    return "critical";
  }

  if (["DISTRACTED", "LANE_DEPARTURE", "TAILGATING"].includes(normalized)) {
    return "moderate";
  }

  return "advisory";
}
