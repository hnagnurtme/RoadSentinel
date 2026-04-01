import { Alert, formatAlertTypeLabel } from "@/types/alert";
import { AlertSeverityBadge } from "@/features/alerts/components/AlertSeverityBadge";

interface AlertsTableProps {
  alerts: Alert[];
  newAlertIds: Set<string>;
  isLoading: boolean;
  errorMessage: string | null;
  onReview: (alert: Alert) => void;
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "N/A";
  }

  return new Date(value).toLocaleString();
}

function formatLocation(latitude: number | null, longitude: number | null): string {
  if (latitude == null || longitude == null) {
    return "Unknown";
  }

  return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
}

function driverName(alert: Alert): string {
  return alert.user?.name ?? alert.driverId ?? "Unknown Driver";
}

function plateNumber(alert: Alert): string {
  return alert.vehicle?.plateNumber ?? alert.vehicleId ?? alert.deviceId;
}

export function AlertsTable({ alerts, newAlertIds, isLoading, errorMessage, onReview }: AlertsTableProps) {
  return (
    <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm overflow-hidden mb-12">
      <div className="px-6 py-4 border-b border-outline-variant/20 flex justify-between items-center bg-surface-container-low/50">
        <h3 className="text-sm font-bold text-primary uppercase tracking-wider">Live Incident Feed</h3>
        <span className="text-[10px] font-bold text-outline uppercase">Real-time update active</span>
      </div>

      {errorMessage && (
        <div className="px-6 py-3 text-xs font-semibold bg-error-container text-on-error-container">{errorMessage}</div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-surface-container-low border-b border-surface-container-high">
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Timestamp</th>
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Driver / Plate</th>
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Severity</th>
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Violation Type</th>
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Geo-Location</th>
              <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">Response</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-container-high">
            {isLoading ? (
              <tr>
                <td className="px-6 py-10 text-sm text-secondary" colSpan={6}>
                  Loading alerts from backend...
                </td>
              </tr>
            ) : alerts.length === 0 ? (
              <tr>
                <td className="px-6 py-10 text-sm text-secondary" colSpan={6}>
                  No alerts available.
                </td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr
                  key={alert.id}
                  className={`hover:bg-surface-container-low transition-colors cursor-pointer ${
                    newAlertIds.has(alert.id) ? "alert-flash" : ""
                  }`}
                  onClick={() => onReview(alert)}
                >
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">
                    <div className="flex items-center gap-2">
                      <span>{formatTimestamp(alert.createdAt)}</span>
                      {newAlertIds.has(alert.id) && <span className="new-alert-badge">NEW</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-xs font-bold text-primary">
                    <div>{driverName(alert)}</div>
                    <div className="text-[10px] font-medium text-secondary mt-1">{plateNumber(alert)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <AlertSeverityBadge alertType={alert.alertType} />
                  </td>
                  <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">
                    {formatAlertTypeLabel(alert.alertType)}
                  </td>
                  <td className="px-6 py-4 text-xs text-secondary">{formatLocation(alert.latitude, alert.longitude)}</td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center gap-2">
                      <button
                        type="button"
                        onClick={() => onReview(alert)}
                        className="bg-primary text-on-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:opacity-90 shadow-sm transition-opacity"
                      >
                        Review
                      </button>
                      <button
                        type="button"
                        className="ring-1 ring-outline-variant/15 text-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:bg-surface-container-low transition-colors bg-surface-container-lowest"
                      >
                        Log
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
