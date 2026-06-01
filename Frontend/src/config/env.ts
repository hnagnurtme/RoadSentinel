const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1";
const DEFAULT_WS_ALERTS_URL = "ws://127.0.0.1:8000/api/v1/ws/alerts";
const DEFAULT_WS_APPEALS_URL = "ws://127.0.0.1:8000/api/v1/ws/appeals";

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  wsAlertsUrl: import.meta.env.VITE_WS_ALERTS_URL ?? DEFAULT_WS_ALERTS_URL,
  wsAppealsUrl: import.meta.env.VITE_WS_APPEALS_URL ?? DEFAULT_WS_APPEALS_URL,
  cloudinaryCloudName: import.meta.env.VITE_CLOUDINARY_CLOUD_NAME ?? "",
  cloudinaryApiKey: import.meta.env.VITE_CLOUDINARY_API_KEY ?? "",
  cloudinaryApiSecret: import.meta.env.VITE_CLOUDINARY_API_SECRET ?? "",
};
