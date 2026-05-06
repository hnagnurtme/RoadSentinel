import { useEffect, useMemo, useRef, useState } from "react";
import { listAppealsAdmin, reviewAppeal } from "@/api/appeals";
import { getUsers, type User } from "@/api/users";
import { listAlerts } from "@/api/alerts";
import { ApiError } from "@/api/http";
import { env } from "@/config/env";
import type { Appeal, AppealApiDto } from "@/types/appeal";
import type { Alert } from "@/types/alert";
import { Check, X, Paperclip, MessageSquareWarning, ExternalLink } from "lucide-react";
import { formatAlertTypeLabel } from "@/types/alert";

function formatTs(value: string | null): string {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

function appealStatusClass(status: string): string {
  if (status === "APPROVED") return "bg-emerald-100 text-emerald-700 border border-emerald-200";
  if (status === "REJECTED") return "bg-rose-100 text-rose-700 border border-rose-200";
  return "bg-amber-100 text-amber-700 border border-amber-200";
}

export function AdminAppeals() {
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [drivers, setDrivers] = useState<Record<string, User>>({});
  const [alerts, setAlerts] = useState<Record<string, Alert>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noteById, setNoteById] = useState<Record<string, string>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [toasts, setToasts] = useState<Array<{ id: number; message: string }>>([]);
  const pageSize = 8;
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

  useEffect(() => {
    let cancelled = false;
    
    Promise.all([
      listAppealsAdmin(),
      getUsers(),
      listAlerts(100)
    ])
      .then(([appealRows, userRows, alertRows]) => {
        if (cancelled) return;
        setAppeals(appealRows);
        
        const driverMap: Record<string, User> = {};
        userRows.forEach(u => driverMap[u.id] = u);
        setDrivers(driverMap);
        
        const alertMap: Record<string, Alert> = {};
        alertRows.forEach(a => alertMap[a.id] = a);
        setAlerts(alertMap);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          setError("Your admin session expired. Please login again.");
          return;
        }
        setError("Unable to load data.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
      
    return () => {
      cancelled = true;
    };
  }, []);

  const totalPages = Math.max(1, Math.ceil(appeals.length / pageSize));
  const pagedAppeals = useMemo(() => {
    const start = (page - 1) * pageSize;
    return appeals.slice(start, start + pageSize);
  }, [appeals, page]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let heartbeatTimer: number | null = null;
    let reconnectTimer: number | null = null;
    let manuallyClosed = false;

    const refreshAppeals = async () => {
      try {
        const rows = await listAppealsAdmin();
        setAppeals(rows);
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 401) {
          setError("Your admin session expired. Please login again.");
          return;
        }
        setError("Realtime sync failed.");
      }
    };

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
          if (payload.event === "appeal.created") {
            pushToast("New appeal received from driver.");
          }
          void refreshAppeals();
        } catch {
          setError("Realtime payload error.");
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
  }, []);

  const onReview = async (appealId: string, status: "APPROVED" | "REJECTED") => {
    setSubmittingId(appealId);
    try {
      const updated = await reviewAppeal(appealId, {
        status,
        adminNote: noteById[appealId] ?? "",
      });
      setAppeals((prev) => prev.map((item) => (item.id === appealId ? updated : item)));
      pushToast(status === "APPROVED" ? "Appeal approved successfully." : "Appeal rejected successfully.");
    } catch {
      setError("Failed to review appeal. Please retry.");
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <div className="p-10 max-w-[1600px] space-y-6">
      <div>
        <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface-variant block mb-2">
          Admin review
        </span>
        <h2 className="text-3xl font-black text-primary tracking-tight">Appeal Management</h2>
      </div>

      {error && <div className="text-sm font-semibold bg-error-container text-on-error-container px-4 py-3 rounded-xl">{error}</div>}

      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-secondary">Created</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-secondary">Driver & Alert ID</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-secondary">Description & Attachment</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">Status</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-secondary">Admin Note</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              {loading ? (
                <tr>
                  <td className="px-6 py-10 text-secondary text-sm text-center" colSpan={6}>
                    Loading appeals...
                  </td>
                </tr>
              ) : appeals.length === 0 ? (
                <tr>
                  <td className="px-6 py-10 text-secondary text-sm text-center flex flex-col items-center justify-center gap-2" colSpan={6}>
                    <MessageSquareWarning className="w-8 h-8 opacity-50" />
                    No appeals yet.
                  </td>
                </tr>
              ) : (
                pagedAppeals.map((appeal) => {
                  const reviewed = appeal.status !== "PENDING";
                  const driver = drivers[appeal.driverId];
                  const driverName = driver ? [driver.name?.given, driver.name?.family].filter(Boolean).join(" ") || driver.email : appeal.driverId.split('-')[0] + "...";
                  const alert = alerts[appeal.alertId];
                  const alertType = alert ? formatAlertTypeLabel(alert.alertType) : appeal.alertId.split('-')[0] + "...";
                  const vehicleText = alert?.vehicle ? `${alert.vehicle.plateNumber} - ${alert.vehicle.manufacturer}` : "Unknown Vehicle";

                  return (
                    <tr key={appeal.id} className="hover:bg-surface-container-low/70 transition-colors align-top">
                      <td className="px-6 py-4">
                        <span className="text-xs font-medium text-on-surface-variant whitespace-nowrap">
                          {formatTs(appeal.createdAt)}
                        </span>
                      </td>
                      <td className="px-6 py-4 space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-secondary uppercase w-12">Driver:</span>
                          <span className="text-xs font-semibold text-primary" title={appeal.driverId}>
                            {driverName}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-secondary uppercase w-12">Vehicle:</span>
                          <span className="text-xs font-semibold text-secondary">
                            {vehicleText}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-secondary uppercase w-12">Alert:</span>
                          <span className="text-xs font-semibold text-error" title={appeal.alertId}>
                            {alertType}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 max-w-[280px]">
                        <p className="text-xs text-secondary line-clamp-3 mb-2">{appeal.description || <span className="italic opacity-50">No description provided</span>}</p>
                        {appeal.attachmentUrl && (
                          <a 
                            href={appeal.attachmentUrl} 
                            target="_blank" 
                            rel="noreferrer" 
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold uppercase rounded bg-surface-container-high text-primary hover:bg-surface-container-highest transition-colors border border-outline-variant/30"
                          >
                            <Paperclip className="w-3.5 h-3.5" />
                            View Attachment
                          </a>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${appealStatusClass(appeal.status)}`}>
                          {appeal.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 min-w-[220px]">
                        <textarea
                          value={noteById[appeal.id] ?? appeal.adminNote ?? ""}
                          onChange={(event) =>
                            setNoteById((prev) => ({
                              ...prev,
                              [appeal.id]: event.target.value,
                            }))
                          }
                          disabled={reviewed}
                          placeholder={reviewed ? "No note provided" : "Write a note..."}
                          rows={2}
                          className="w-full rounded-lg border border-outline-variant/40 bg-surface px-3 py-2 text-xs text-primary disabled:opacity-60 focus:ring-2 focus:ring-primary/30 outline-none resize-none"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <button
                            type="button"
                            disabled={reviewed || submittingId === appeal.id}
                            onClick={() => onReview(appeal.id, "APPROVED")}
                            className="w-full inline-flex items-center justify-center gap-1.5 text-[10px] font-bold uppercase px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-700 hover:bg-emerald-200 disabled:opacity-50 disabled:grayscale transition-colors border border-emerald-200"
                          >
                            <Check className="w-3.5 h-3.5" />
                            Approve
                          </button>
                          <button
                            type="button"
                            disabled={reviewed || submittingId === appeal.id}
                            onClick={() => onReview(appeal.id, "REJECTED")}
                            className="w-full inline-flex items-center justify-center gap-1.5 text-[10px] font-bold uppercase px-3 py-1.5 rounded-lg bg-rose-100 text-rose-700 hover:bg-rose-200 disabled:opacity-50 disabled:grayscale transition-colors border border-rose-200"
                          >
                            <X className="w-3.5 h-3.5" />
                            Reject
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {!loading && appeals.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-secondary">
            Page {page} / {totalPages} - {appeals.length} appeals
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 text-xs font-semibold rounded border border-outline-variant/40 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 text-xs font-semibold rounded border border-outline-variant/40 disabled:opacity-50"
            >
              Next
            </button>
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
    </div>
  );
}
