import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Video } from "lucide-react";
import { listAlerts } from "@/api/alerts";
import type { Alert } from "@/types/alert";
import { formatAlertTypeLabel } from "@/types/alert";
import { AlertSeverityBadge } from "@/features/alerts/components/AlertSeverityBadge";
import { DriverHeader } from "@/components/DriverHeader";

function formatTs(value: string | null): string {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

export function DriverViolations() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listAlerts(50)
      .then((rows) => {
        if (!cancelled) setAlerts(rows);
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load violation list.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <DriverHeader />
      <div className="p-10 max-w-[1400px] space-y-6">
        <div className="flex justify-between items-end">
          <div>
            <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface-variant block mb-2">
              Violation evidence
            </span>
            <h2 className="text-3xl font-black text-primary tracking-tight flex items-center gap-3">
              <Video className="w-8 h-8" />
              Violation Evidence
            </h2>
            <p className="text-secondary text-sm mt-1 font-medium">Only incidents linked to your account are displayed.</p>
          </div>
        </div>

        {error && <div className="text-sm font-semibold bg-error-container text-on-error-container px-4 py-3 rounded-xl">{error}</div>}

        <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-outline-variant/20 bg-surface-container-low/50">
            <h3 className="text-sm font-bold text-primary uppercase tracking-wider">Violation Timeline</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-surface-container-low border-b border-surface-container-high">
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Timestamp</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Severity</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Violation Type</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container-high">
                {loading ? (
                  <tr>
                    <td className="px-6 py-10 text-secondary text-sm" colSpan={4}>
                      Loading...
                    </td>
                  </tr>
                ) : alerts.length === 0 ? (
                  <tr>
                    <td className="px-6 py-10 text-secondary text-sm" colSpan={4}>
                      No violations found.
                    </td>
                  </tr>
                ) : (
                  alerts.map((a) => (
                    <tr
                      key={a.id}
                      className="hover:bg-surface-container-low cursor-pointer transition-colors"
                      onClick={() => navigate(`/driver/violations/${a.id}`, { state: { alert: a } })}
                    >
                      <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">{formatTs(a.createdAt)}</td>
                      <td className="px-6 py-4">
                        <AlertSeverityBadge alertType={a.alertType} />
                      </td>
                      <td className="px-6 py-4 text-xs font-medium text-primary">{formatAlertTypeLabel(a.alertType)}</td>
                      <td className="px-6 py-4 text-xs text-secondary">{a.evidenceUrl ? "Available" : "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}