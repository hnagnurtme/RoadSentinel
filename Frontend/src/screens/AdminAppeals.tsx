import { useEffect, useMemo, useRef, useState } from "react";
import { listAppealsAdmin, reviewAppeal } from "@/api/appeals";
import { getUsers, type User } from "@/api/users";
import { listAlerts } from "@/api/alerts";
import { ApiError } from "@/api/http";
import { env } from "@/config/env";
import type { Appeal, AppealApiDto } from "@/types/appeal";
import type { Alert } from "@/types/alert";
import { Check, X, Paperclip, MessageSquareWarning, ExternalLink, Search, FileVideo } from "lucide-react";
import { formatAlertTypeLabel } from "@/types/alert";
import { useLanguage } from "@/i18n/LanguageContext";
import { calculateSafetyScore, getSafetyScoreLabel } from "@/utils/safetyScore";
import { LoadingRadar } from "@/components/LoadingRadar";

function formatTs(value: string | null): string {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

function isVideoEvidence(url: string | null): boolean {
  if (!url) return false;
  const normalized = url.toLowerCase();
  return normalized.endsWith(".mp4") || normalized.includes("/video/");
}

function appealStatusClass(status: string): string {
  if (status === "APPROVED") return "bg-emerald-500/10 text-emerald-600";
  if (status === "REJECTED") return "bg-error/10 text-error";
  return "bg-amber-500/10 text-amber-600";
}

function resolveExternalUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^(https?:|blob:|data:)/i.test(trimmed)) return trimmed;

  const apiOrigin = env.apiBaseUrl.replace(/\/api\/v\d+\/?$/i, "");
  if (trimmed.startsWith("/")) return `${apiOrigin}${trimmed}`;
  return `${apiOrigin}/${trimmed}`;
}

export function AdminAppeals() {
  const { t, language } = useLanguage();
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [drivers, setDrivers] = useState<Record<string, User>>({});
  const [alerts, setAlerts] = useState<Record<string, Alert>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noteById, setNoteById] = useState<Record<string, string>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  
  const [selectedAppeal, setSelectedAppeal] = useState<Appeal | null>(null);
  const [previewEvidenceUrl, setPreviewEvidenceUrl] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PENDING" | "APPROVED" | "REJECTED">("ALL");
  const [sortBy, setSortBy] = useState<"DEFAULT" | "NEWEST" | "OLDEST">("DEFAULT");

  const statusFilters = [
    { value: "ALL", label: language === "en" ? "All" : "Tất cả" },
    { value: "PENDING", label: language === "en" ? "Pending" : "Chờ duyệt" },
    { value: "APPROVED", label: language === "en" ? "Approved" : "Đã nhận" },
    { value: "REJECTED", label: language === "en" ? "Rejected" : "Từ chối" },
  ];

  const sortOptions = [
    { value: "DEFAULT", label: language === "en" ? "Pending First" : "Ưu tiên chờ duyệt" },
    { value: "NEWEST", label: language === "en" ? "Newest First" : "Mới nhất trước" },
    { value: "OLDEST", label: language === "en" ? "Oldest First" : "Cũ nhất trước" },
  ];

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

        // Keep selectedAppeal synced if it was updated
        setSelectedAppeal(prev => {
          if (!prev) return null;
          return appealRows.find(item => item.id === prev.id) || prev;
        });
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

  useEffect(() => {
    let ws: WebSocket | null = null;
    let heartbeatTimer: number | null = null;
    let reconnectTimer: number | null = null;
    let manuallyClosed = false;

    const refreshAppeals = async () => {
      try {
        const rows = await listAppealsAdmin();
        setAppeals(rows);
        setSelectedAppeal(prev => {
          if (!prev) return null;
          return rows.find(item => item.id === prev.id) || prev;
        });
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
      setSelectedAppeal(updated);
      pushToast(status === "APPROVED" ? "Appeal approved successfully." : "Appeal rejected successfully.");
    } catch {
      setError("Failed to review appeal. Please retry.");
    } finally {
      setSubmittingId(null);
    }
  };

  const processedAppeals = useMemo(() => {
    let result = appeals.filter((appeal) => {
      const driver = drivers[appeal.driverId];
      const driverName = driver ? driver.name || driver.email : "";
      const alert = alerts[appeal.alertId];
      const alertType = alert ? formatAlertTypeLabel(alert.alertType) : "";
      
      const searchLower = searchTerm.toLowerCase();
      return (
        driverName.toLowerCase().includes(searchLower) ||
        alertType.toLowerCase().includes(searchLower) ||
        appeal.status.toLowerCase().includes(searchLower)
      );
    });

    if (statusFilter !== "ALL") {
      result = result.filter((appeal) => appeal.status === statusFilter);
    }

    result.sort((a, b) => {
      const dateA = new Date(a.createdAt).getTime();
      const dateB = new Date(b.createdAt).getTime();

      if (sortBy === "NEWEST") {
        return dateB - dateA;
      }
      if (sortBy === "OLDEST") {
        return dateA - dateB;
      }
      
      // DEFAULT: PENDING first, then NEWEST
      if (a.status === "PENDING" && b.status !== "PENDING") {
        return -1;
      }
      if (a.status !== "PENDING" && b.status === "PENDING") {
        return 1;
      }
      return dateB - dateA;
    });

    return result;
  }, [appeals, drivers, alerts, searchTerm, statusFilter, sortBy]);

  const selectedAlert = selectedAppeal ? alerts[selectedAppeal.alertId] ?? null : null;
  const selectedEvidenceUrl = resolveExternalUrl(selectedAlert?.evidenceUrl);
  const selectedAttachmentUrl = resolveExternalUrl(selectedAppeal?.attachmentUrl);
  const hasReviewAssets = selectedAttachmentUrl || selectedEvidenceUrl;

  return (
    <div className="flex flex-col h-full bg-surface-container-lowest relative">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-6 border-b border-surface-container-high bg-surface-container-lowest/80 backdrop-blur-xl sticky top-0 z-20 gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight text-primary">{t("appeals.title")}</h1>
          <p className="text-sm text-secondary">{t("appeals.subtitle")}</p>
        </div>
        
        <div className="flex items-center gap-4 flex-1 max-w-md ml-auto">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-secondary" />
            <input
              type="text"
              placeholder={t("common.search")}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-surface-container rounded-lg pl-9 pr-4 py-2 text-sm focus:ring-2 focus:ring-primary outline-none border border-outline-variant/10"
            />
          </div>
        </div>
      </div>

      {error && <div className="mx-8 mt-6 text-sm font-semibold bg-error-container text-on-error-container px-4 py-3 rounded-xl">{error}</div>}

      <div className="flex-1 flex overflow-hidden">
        {/* Left Side: Appeals List */}
        <div className="w-1/3 border-r border-surface-container-high bg-surface-container-lowest/50 flex flex-col">
          {/* Controls Bar */}
          <div className="p-4 border-b border-surface-container-high flex flex-col gap-3 bg-surface-container-lowest/80 backdrop-blur-md shrink-0">
            {/* Status Filter Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 custom-scrollbar">
              {statusFilters.map((tab) => {
                const isSelected = statusFilter === tab.value;
                return (
                  <button
                    key={tab.value}
                    onClick={() => setStatusFilter(tab.value as any)}
                    className={`px-3 py-1 rounded-full text-[11px] font-bold tracking-wide transition-all duration-200 cursor-pointer whitespace-nowrap ${
                      isSelected
                        ? "bg-primary text-on-primary shadow-sm"
                        : "bg-surface-container-high/60 text-secondary hover:bg-surface-container-high hover:text-primary"
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Sort Selector */}
            <div className="flex items-center justify-between text-xs">
              <span className="text-secondary font-medium">
                {language === "en" ? "Sort by:" : "Sắp xếp theo:"}
              </span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-surface-container-high/40 text-on-surface hover:bg-surface-container-high/80 rounded-lg px-2.5 py-1.5 font-semibold text-xs border-0 focus:ring-1 focus:ring-primary/30 outline-none cursor-pointer transition-colors"
              >
                {sortOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-surface-container-high">
            {loading ? (
              <LoadingRadar message={t("common.loading")} minHeight="min-h-[400px]" />
            ) : processedAppeals.length === 0 ? (
              <div className="p-8 text-center text-secondary text-sm">
                {t("appeals.noAppealsFound")}
              </div>
            ) : (
              processedAppeals.map((appeal) => {
                const driver = drivers[appeal.driverId];
                const driverName = driver
                  ? driver.name || driver.email
                  : appeal.driverId.split('-')[0] + "...";
                const alert = alerts[appeal.alertId];
                const alertType = alert ? formatAlertTypeLabel(alert.alertType) : appeal.alertId.split('-')[0] + "...";
                const isActive = selectedAppeal?.id === appeal.id;
                
                return (
                  <button
                    key={appeal.id}
                    onClick={() => setSelectedAppeal(appeal)}
                    className={`flex items-start gap-4 py-5 px-4 text-left w-full transition-colors border-l-4 cursor-pointer ${
                      isActive
                        ? "bg-primary/10 border-primary"
                        : "hover:bg-surface-container-low border-transparent"
                    }`}
                  >
                    <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center shrink-0 overflow-hidden">
                      {driver?.avatar_image_url ? (
                        <img src={driver.avatar_image_url} alt={driverName} className="w-full h-full object-cover" />
                      ) : (
                        <MessageSquareWarning className="w-5 h-5 text-secondary" />
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="font-bold text-on-surface truncate text-sm">
                          {driverName}
                        </h3>
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide shrink-0 ${appealStatusClass(appeal.status)}`}>
                          {appeal.status === "PENDING" ? t("appeals.pending") : appeal.status === "APPROVED" ? t("appeals.approved") : t("appeals.rejected")}
                        </span>
                      </div>
                      
                      <p className="text-xs text-error font-medium truncate mt-0.5">
                        {alertType}
                      </p>
                      <p className="text-[10px] text-secondary mt-1">
                        {formatTs(appeal.createdAt)}
                      </p>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Selected Appeal Details */}
        <div className="flex-1 overflow-y-auto p-8 bg-surface-container-lowest">
          {selectedAppeal ? (
            <div className="max-w-4xl mx-auto flex flex-col gap-4 relative animate-in fade-in duration-300">
              {/* Profile Header */}
              <div className="bg-surface-container rounded-2xl p-4 flex items-start gap-4 relative">
                <button
                  onClick={() => setSelectedAppeal(null)}
                  className="absolute top-4 right-4 p-2 rounded-lg bg-surface-container-high text-secondary hover:text-primary transition-colors cursor-pointer"
                  title={t("common.close")}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
                
                <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center shrink-0 overflow-hidden">
                  {drivers[selectedAppeal.driverId]?.avatar_image_url ? (
                    <img
                      src={drivers[selectedAppeal.driverId].avatar_image_url}
                      alt={drivers[selectedAppeal.driverId].name || "Driver"}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <MessageSquareWarning className="w-7 h-7 text-primary" />
                  )}
                </div>

                <div className="flex-1 pr-12">
                  <span className="text-[9px] font-black text-primary bg-primary/10 px-2 py-0.5 rounded uppercase tracking-wider font-mono self-start inline-block">
                    {t("appeals.appealCase")}
                  </span>
                  <h2 className="text-lg font-bold text-on-surface mt-1">
                    {drivers[selectedAppeal.driverId]
                      ? drivers[selectedAppeal.driverId].name || drivers[selectedAppeal.driverId].email
                      : selectedAppeal.driverId}
                  </h2>
                  <p className="text-xs text-secondary mt-0.5">
                    {drivers[selectedAppeal.driverId]?.email}
                  </p>
                  
                  {(() => {
                    const driverAlerts = (Object.values(alerts) as Alert[]).filter(a => a.driverId === selectedAppeal.driverId);
                    const driverAppeals = appeals.filter(ap => ap.driverId === selectedAppeal.driverId);
                    const score = calculateSafetyScore(selectedAppeal.driverId, driverAlerts, driverAppeals, true);
                    const scoreInfo = getSafetyScoreLabel(score, language);
                    return (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[10px] text-secondary font-bold uppercase tracking-wider">{t("drivers.safetyScore")}:</span>
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${scoreInfo.colorClass}`}>
                          {score}/100 — {scoreInfo.label}
                        </span>
                      </div>
                    );
                  })()}
                </div>
              </div>

              {/* Appeal Details Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
                {/* Incident & Appeal Details Card */}
                <div className="flex flex-col gap-2.5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5">
                    <MessageSquareWarning className="w-4 h-4 text-primary" /> {t("appeals.appealDetails")}
                  </h3>
                  <div className="bg-surface-container rounded-xl p-4 flex flex-col gap-3 flex-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-secondary font-medium">{t("sidebar.alerts")}</span>
                      <span className="text-error font-bold">
                        {alerts[selectedAppeal.alertId]
                          ? formatAlertTypeLabel(alerts[selectedAppeal.alertId].alertType)
                          : selectedAppeal.alertId}
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-surface-container-high pt-3 text-xs">
                      <span className="text-secondary font-medium">{t("vehicles.plateNumber")}</span>
                      <span className="text-on-surface font-bold">
                        {alerts[selectedAppeal.alertId]?.vehicle ? (
                          <>
                            <span className="font-mono">{alerts[selectedAppeal.alertId].vehicle.plateNumber}</span>
                            {" - " + alerts[selectedAppeal.alertId].vehicle.manufacturer}
                          </>
                        ) : (
                          "Unknown Vehicle"
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-surface-container-high pt-3 text-xs">
                      <span className="text-secondary font-medium">{t("common.time")}</span>
                      <span className="text-on-surface font-bold">
                        {formatTs(selectedAppeal.createdAt)}
                      </span>
                    </div>

                    <div className="flex flex-col gap-2 border-t border-surface-container-high pt-3">
                      <span className="text-[10px] font-bold text-secondary">{t("appeals.driverNotes")}</span>
                      <p className="text-xs text-on-surface bg-surface-container-low p-3 rounded-lg border border-outline-variant/10 min-h-[70px] whitespace-pre-line leading-relaxed">
                        {selectedAppeal.description || <span className="italic opacity-55">{t("appeals.noDescription")}</span>}
                      </p>
                    </div>

                    {hasReviewAssets && (
                      <div className="flex flex-col gap-2 border-t border-surface-container-high pt-3">
                        <span className="text-[10px] font-bold text-secondary">{t("appeals.reviewFiles")}</span>
                        <div className="flex flex-wrap gap-2">
                          {selectedAttachmentUrl && (
                            <a
                              href={selectedAttachmentUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-high hover:bg-surface-container-highest transition-colors border border-outline-variant/30 text-[10px] font-bold uppercase text-primary cursor-pointer shadow-sm text-center"
                            >
                              <Paperclip className="w-3.5 h-3.5 shrink-0" />
                              {t("appeals.viewAttachment")}
                              <ExternalLink className="w-3 h-3 ml-0.5 opacity-55 shrink-0" />
                            </a>
                          )}

                          {selectedEvidenceUrl && (
                            <button
                              type="button"
                              onClick={() => setPreviewEvidenceUrl(selectedEvidenceUrl)}
                              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary text-on-primary hover:opacity-90 transition-opacity border border-primary/30 text-[10px] font-bold uppercase cursor-pointer shadow-sm text-center"
                            >
                              <FileVideo className="w-3.5 h-3.5 shrink-0" />
                              {t("appeals.viewEvidence")}
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Review note and Actions Card */}
                <div className="flex flex-col gap-2.5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5">
                    <Check className="w-4 h-4 text-primary" /> {t("appeals.actions")}
                  </h3>
                  <div className="bg-surface-container rounded-xl p-4 flex flex-col gap-3 flex-1 justify-between">
                    <div className="flex flex-col gap-3">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-secondary font-medium">{t("appeals.appealStatus")}</span>
                        <div className="self-start">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${appealStatusClass(selectedAppeal.status)}`}>
                            {selectedAppeal.status === "PENDING" ? t("appeals.pending") : selectedAppeal.status === "APPROVED" ? t("appeals.approved") : t("appeals.rejected")}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-col gap-2 border-t border-surface-container-high pt-3">
                        <label className="text-[10px] font-bold text-secondary">{t("appeals.adminNoteLabel")}</label>
                        <textarea
                          value={noteById[selectedAppeal.id] ?? selectedAppeal.adminNote ?? ""}
                          onChange={(event) =>
                            setNoteById((prev) => ({
                              ...prev,
                              [selectedAppeal.id]: event.target.value,
                            }))
                          }
                          disabled={selectedAppeal.status !== "PENDING"}
                          placeholder={selectedAppeal.status !== "PENDING" ? t("appeals.noAdminNote") : t("appeals.writeAdminNote")}
                          rows={4}
                          className="w-full rounded-xl border border-outline-variant/40 bg-surface px-3 py-2 text-xs text-primary disabled:opacity-60 focus:ring-2 focus:ring-primary/30 outline-none resize-none"
                        />
                      </div>
                    </div>

                    {selectedAppeal.status === "PENDING" && (
                      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-surface-container-high mt-3">
                        <button
                          type="button"
                          disabled={submittingId === selectedAppeal.id}
                          onClick={() => onReview(selectedAppeal.id, "APPROVED")}
                          className="flex items-center justify-center gap-1 py-2 rounded-lg bg-emerald-600 text-white font-bold text-[10px] hover:opacity-90 disabled:opacity-50 disabled:grayscale transition-all cursor-pointer shadow-sm"
                        >
                          <Check className="w-3.5 h-3.5" />
                          {t("appeals.approveBtn")}
                        </button>
                        <button
                          type="button"
                          disabled={submittingId === selectedAppeal.id}
                          onClick={() => onReview(selectedAppeal.id, "REJECTED")}
                          className="flex items-center justify-center gap-1 py-2 rounded-lg bg-error text-on-error font-bold text-[10px] hover:opacity-90 disabled:opacity-50 disabled:grayscale transition-all cursor-pointer shadow-sm"
                        >
                          <X className="w-3.5 h-3.5" />
                          {t("appeals.rejectBtn")}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-secondary">
              <MessageSquareWarning className="w-16 h-16 mb-4 opacity-20" />
              <p>{t("appeals.selectAppeal")}</p>
            </div>
          )}
        </div>
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
              <h4 className="text-sm font-bold text-primary uppercase tracking-wider">
                {language === "en" ? "Evidence Preview" : "Xem trước bằng chứng"}
              </h4>
              <div className="flex items-center gap-2">
                <a
                  href={previewEvidenceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
                >
                  {language === "en" ? "Open Original" : "Mở bản gốc"} <ExternalLink className="w-3.5 h-3.5" />
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewEvidenceUrl(null)}
                  className="p-1.5 rounded hover:bg-surface-container-low text-secondary cursor-pointer"
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

