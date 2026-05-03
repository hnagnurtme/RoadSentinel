import { useEffect, useMemo, useRef, useState } from "react";
import { listAppealsAdmin, reviewAppeal } from "@/api/appeals";
import { ApiError } from "@/api/http";
import { env } from "@/config/env";
import type { Appeal } from "@/types/appeal";
import type { AppealApiDto } from "@/types/appeal";

function formatTs(value: string | null): string {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

export function AdminAppeals() {
  const [appeals, setAppeals] = useState<Appeal[]>([]);
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
    listAppealsAdmin()
      .then((rows) => {
        if (!cancelled) setAppeals(rows);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          setError("Your admin session expired. Please login again.");
          return;
        }
        setError("Unable to load appeals.");
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
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Created</th>
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Driver</th>
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Alert</th>
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Description</th>
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Attachment</th>
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Status</th>
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">Admin Note</th>
                <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              {loading ? (
                <tr>
                  <td className="px-4 py-10 text-secondary text-sm" colSpan={8}>
                    Loading...
                  </td>
                </tr>
              ) : appeals.length === 0 ? (
                <tr>
                  <td className="px-4 py-10 text-secondary text-sm" colSpan={8}>
                    No appeals yet.
                  </td>
                </tr>
              ) : (
                pagedAppeals.map((appeal) => {
                  const reviewed = appeal.status !== "PENDING";
                  return (
                    <tr key={appeal.id} className="hover:bg-surface-container-low/70 transition-colors align-top">
                      <td className="px-4 py-4 text-xs text-secondary">{formatTs(appeal.createdAt)}</td>
                      <td className="px-4 py-4 text-xs text-primary font-semibold">{appeal.driverId}</td>
                      <td className="px-4 py-4 text-xs text-secondary">{appeal.alertId}</td>
                      <td className="px-4 py-4 text-xs text-secondary max-w-xs">{appeal.description || "-"}</td>
                      <td className="px-4 py-4 text-xs">
                        {appeal.attachmentUrl ? (
                          <a href={appeal.attachmentUrl} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                            Open
                          </a>
                        ) : (
                          <span className="text-outline">-</span>
                        )}
                      </td>
                      <td className="px-4 py-4 text-xs font-bold">{appeal.status}</td>
                      <td className="px-4 py-4 min-w-[220px]">
                        <textarea
                          value={noteById[appeal.id] ?? appeal.adminNote ?? ""}
                          onChange={(event) =>
                            setNoteById((prev) => ({
                              ...prev,
                              [appeal.id]: event.target.value,
                            }))
                          }
                          disabled={reviewed}
                          rows={2}
                          className="w-full rounded border border-outline-variant/40 bg-surface px-2 py-1 text-xs text-primary disabled:opacity-60"
                        />
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex justify-center gap-2">
                          <button
                            type="button"
                            disabled={reviewed || submittingId === appeal.id}
                            onClick={() => onReview(appeal.id, "APPROVED")}
                            className="text-[10px] font-bold uppercase px-2 py-1 rounded bg-emerald-600 text-white disabled:opacity-50"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            disabled={reviewed || submittingId === appeal.id}
                            onClick={() => onReview(appeal.id, "REJECTED")}
                            className="text-[10px] font-bold uppercase px-2 py-1 rounded bg-rose-600 text-white disabled:opacity-50"
                          >
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
