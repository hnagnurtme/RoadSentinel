const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1";
const DEFAULT_WS_ALERTS_URL = "ws://127.0.0.1:8000/api/v1/ws/alerts";

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  wsAlertsUrl: import.meta.env.VITE_WS_ALERTS_URL ?? DEFAULT_WS_ALERTS_URL,
};
