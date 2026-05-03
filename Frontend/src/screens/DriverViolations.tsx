import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ExternalLink, MessageSquareWarning, Send, Video, X } from "lucide-react";
import { createAppeal, listMyAppeals } from "@/api/appeals";
import { listAlerts } from "@/api/alerts";
import { ApiError } from "@/api/http";
import { env } from "@/config/env";
import { useAuth } from "@/auth/AuthContext";
import { type Appeal, type AppealApiDto, type AppealStatus } from "@/types/appeal";
import type { Alert } from "@/types/alert";
import { formatAlertTypeLabel } from "@/types/alert";
import { AlertSeverityBadge } from "@/features/alerts/components/AlertSeverityBadge";
import { DriverHeader } from "@/components/DriverHeader";

function formatTs(value: string | null): string {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

function isVideoEvidence(url: string | null): boolean {
  if (!url) return false;
  const normalized = url.toLowerCase();
  return normalized.endsWith(".mp4") || normalized.includes("/video/");
}

function appealStatusClass(status: AppealStatus): string {
  if (status === "APPROVED") return "bg-emerald-100 text-emerald-700";
  if (status === "REJECTED") return "bg-rose-100 text-rose-700";
  return "bg-amber-100 text-amber-700";
}

export function DriverViolations() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [appealsByAlert, setAppealsByAlert] = useState<Record<string, Appeal>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewEvidenceUrl, setPreviewEvidenceUrl] = useState<string | null>(null);
  const [appealModalAlert, setAppealModalAlert] = useState<Alert | null>(null);
  const [appealDescription, setAppealDescription] = useState("");
  const [appealAttachmentUrl, setAppealAttachmentUrl] = useState("");
  const [appealSubmitting, setAppealSubmitting] = useState(false);
  const [appealError, setAppealError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Array<{ id: number; message: string }>>([]);
  const lastToastAtRef = useRef<Record<string, number>>({});

  const pushToast = (message: string) => {
    const now = Date.now();
    const lastAt = lastToastAtRef.current[message] ?? 0;
    if (now - lastAt < 1200) {
      return;
    }
    lastToastAtRef.current[message] = now;
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, message }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 3500);
  };

  const refreshAppeals = async () => {
    const appealRows = await listMyAppeals();
    const latestByAlert: Record<string, Appeal> = {};
    for (const appeal of appealRows) {
      const existing = latestByAlert[appeal.alertId];
      if (!existing) {
        latestByAlert[appeal.alertId] = appeal;
        continue;
      }
      const existingTs = existing.createdAt ?? "";
      const candidateTs = appeal.createdAt ?? "";
      if (candidateTs > existingTs) {
        latestByAlert[appeal.alertId] = appeal;
      }
    }
    setAppealsByAlert(latestByAlert);
  };

  useEffect(() => {
    let cancelled = false;
    listAlerts(50)
      .then((alertRows) => {
        if (!cancelled) setAlerts(alertRows);
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load violation list.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    refreshAppeals().catch((err: unknown) => {
      if (cancelled) return;
      if (err instanceof ApiError && err.status === 401) {
        setError("Your driver session expired. Please login again.");
        return;
      }
      setError("Unable to load your appeal status.");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const getApiErrorMessage = (error: unknown): string => {
    if (error instanceof ApiError && error.responseText) {
      try {
        const parsed = JSON.parse(error.responseText) as { message?: string };
        if (parsed.message) return parsed.message;
      } catch {
        return error.message;
      }
      return error.message;
    }
    return "Failed to submit appeal. Please try again.";
  };

  useEffect(() => {
    if (!user?.id) return;

    let ws: WebSocket | null = null;
    let heartbeatTimer: number | null = null;
    let reconnectTimer: number | null = null;
    let manuallyClosed = false;

    const connect = () => {
      ws = new WebSocket(env.wsAppealsUrl);

      ws.onopen = () => {
        heartbeatTimer = window.setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) ws.send("ping");
        }, 10_000);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            event?: "appeal.created" | "appeal.reviewed";
            data?: AppealApiDto;
          };
          if (!payload.event || !payload.data) return;
          if (payload.event !== "appeal.created" && payload.event !== "appeal.reviewed") return;
          if (payload.data.driver_id !== user.id) return;
          if (payload.event === "appeal.reviewed") {
            pushToast(`Your appeal was ${payload.data.status.toLowerCase()}.`);
          } else {
            pushToast("Your appeal is now pending review.");
          }
          void refreshAppeals();
        } catch {
          // keep UI stable if message isn't appeal payload
        }
      };

      ws.onclose = () => {
        if (heartbeatTimer != null) {
          window.clearInterval(heartbeatTimer);
          heartbeatTimer = null;
        }
        if (!manuallyClosed) {
          reconnectTimer = window.setTimeout(connect, 1500);
        }
      };
    };

    connect();
    return () => {
      manuallyClosed = true;
      if (heartbeatTimer != null) window.clearInterval(heartbeatTimer);
      if (reconnectTimer != null) window.clearTimeout(reconnectTimer);
      if (ws && ws.readyState === WebSocket.OPEN) ws.close(1000, "component teardown");
    };
  }, [user?.id]);

  const submitAppeal = async () => {
    if (!appealModalAlert) return;
    setAppealSubmitting(true);
    setAppealError(null);
    try {
      const created = await createAppeal({
        alertId: appealModalAlert.id,
        description: appealDescription.trim(),
        attachmentUrl: appealAttachmentUrl.trim(),
      });
      setAppealsByAlert((prev) => ({ ...prev, [created.alertId]: created }));
      setAppealModalAlert(null);
      setAppealDescription("");
      setAppealAttachmentUrl("");
      pushToast("Appeal submitted successfully.");
    } catch (error) {
      setAppealError(getApiErrorMessage(error));
      await refreshAppeals().catch(() => undefined);
    } finally {
      setAppealSubmitting(false);
    }
  };

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
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">Preview</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">Appeal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container-high">
                {loading ? (
                  <tr>
                    <td className="px-6 py-10 text-secondary text-sm" colSpan={6}>
                      Loading...
                    </td>
                  </tr>
                ) : alerts.length === 0 ? (
                  <tr>
                    <td className="px-6 py-10 text-secondary text-sm" colSpan={6}>
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
                      <td className="px-6 py-4">
                        <div className="flex justify-center">
                          {a.evidenceUrl ? (
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                setPreviewEvidenceUrl(a.evidenceUrl);
                              }}
                              className="inline-flex items-center gap-1.5 bg-primary text-on-primary text-[10px] font-bold uppercase px-3 py-1.5 rounded hover:opacity-90 transition-opacity"
                            >
                              <Video className="w-3.5 h-3.5" />
                              View
                            </button>
                          ) : (
                            <span className="text-[10px] text-outline">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-center gap-2">
                          {appealsByAlert[a.id] ? (
                            <span
                              className={`inline-flex items-center rounded px-2 py-1 text-[10px] font-bold uppercase ${appealStatusClass(appealsByAlert[a.id].status)}`}
                            >
                              {appealsByAlert[a.id].status}
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                setAppealError(null);
                                setAppealModalAlert(a);
                              }}
                              className="inline-flex items-center gap-1.5 bg-surface-container text-primary text-[10px] font-bold uppercase px-3 py-1.5 rounded hover:bg-surface-container-high transition-colors"
                            >
                              <MessageSquareWarning className="w-3.5 h-3.5" />
                              Submit
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {previewEvidenceUrl && (
        <div
          className="fixed inset-0 z-70 bg-black/70 backdrop-blur-[1px] p-4 md:p-8 flex items-center justify-center"
          onClick={() => setPreviewEvidenceUrl(null)}
        >
          <div
            className="w-full max-w-5xl bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/20 shadow-xl overflow-hidden"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="px-5 py-3 border-b border-outline-variant/20 flex items-center justify-between">
              <h4 className="text-sm font-bold text-primary uppercase tracking-wider">Evidence Preview</h4>
              <div className="flex items-center gap-2">
                <a
                  href={previewEvidenceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
                >
                  Open Original <ExternalLink className="w-3.5 h-3.5" />
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewEvidenceUrl(null)}
                  className="p-1.5 rounded hover:bg-surface-container-low text-secondary"
                  aria-label="Close preview"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="bg-black">
              {isVideoEvidence(previewEvidenceUrl) ? (
                <video className="w-full max-h-[72vh]" src={previewEvidenceUrl} controls autoPlay />
              ) : (
                <img className="w-full max-h-[72vh] object-contain mx-auto" src={previewEvidenceUrl} alt="Evidence preview" />
              )}
            </div>
          </div>
        </div>
      )}

      {appealModalAlert && (
        <div
          className="fixed inset-0 z-70 bg-black/50 p-4 md:p-8 flex items-center justify-center"
          onClick={() => setAppealModalAlert(null)}
        >
          <div
            className="w-full max-w-2xl bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/20 shadow-xl overflow-hidden"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="px-5 py-3 border-b border-outline-variant/20 flex items-center justify-between">
              <h4 className="text-sm font-bold text-primary uppercase tracking-wider">Submit Appeal</h4>
              <button
                type="button"
                onClick={() => setAppealModalAlert(null)}
                className="p-1.5 rounded hover:bg-surface-container-low text-secondary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-sm text-secondary">
                Alert: <span className="font-semibold text-primary">{formatAlertTypeLabel(appealModalAlert.alertType)}</span>
              </p>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-secondary uppercase tracking-wide">
                  Description (Optional)
                </label>
                <textarea
                  value={appealDescription}
                  onChange={(event) => setAppealDescription(event.target.value)}
                  rows={4}
                  placeholder="Explain why this violation should be reviewed..."
                  className="w-full rounded-lg border border-outline-variant/40 bg-surface px-3 py-2 text-sm text-primary outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-secondary uppercase tracking-wide">
                  Attachment URL (Optional)
                </label>
                <input
                  value={appealAttachmentUrl}
                  onChange={(event) => setAppealAttachmentUrl(event.target.value)}
                  placeholder="https://..."
                  className="w-full rounded-lg border border-outline-variant/40 bg-surface px-3 py-2 text-sm text-primary outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              {appealError && (
                <div className="text-sm font-semibold bg-error-container text-on-error-container px-4 py-3 rounded-xl">
                  {appealError}
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={submitAppeal}
                  disabled={appealSubmitting}
                  className="inline-flex items-center gap-2 bg-primary text-on-primary text-xs font-bold uppercase px-4 py-2 rounded-lg hover:opacity-90 disabled:opacity-60"
                >
                  <Send className="w-3.5 h-3.5" />
                  {appealSubmitting ? "Submitting..." : "Send Appeal"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="fixed right-4 top-4 z-80 space-y-2">
        {toasts.map((toast) => (
          <div key={toast.id} className="min-w-[260px] rounded-lg bg-primary px-4 py-3 text-xs font-semibold text-on-primary shadow-lg">
            {toast.message}
          </div>
        ))}
      </div>
    </>
  );
}