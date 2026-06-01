import { ArrowLeft, AlertOctagon, Video, Paperclip, Send, Clock, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { Alert, formatAlertTypeLabel, getAlertSeverity } from "@/types/alert";
import { useLanguage } from "@/i18n/LanguageContext";
import React, { useState, useEffect } from "react";
import { useAuth } from "@/auth/AuthContext";
import { createAppeal, listMyAppeals, listAppealsAdmin } from "@/api/appeals";
import type { Appeal } from "@/types/appeal";
import { ImageUploader } from "@/components/ImageUploader";

interface IncidentReviewProps {
  alert: Alert | null;
  onNavigate: (view: "dashboard" | "incident" | "alerts") => void;
  onBack?: () => void;
  backLabel?: string;
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "N/A";
  }

  return new Date(value).toLocaleString();
}

function locationLabel(alert: Alert): string {
  if (alert.latitude == null || alert.longitude == null) {
    return "Unknown";
  }

  return `${alert.latitude.toFixed(4)}, ${alert.longitude.toFixed(4)}`;
}

function severityLabel(alertType: string): string {
  const severity = getAlertSeverity(alertType);
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

function isVideoEvidence(url: string | null): boolean {
  if (!url) {
    return false;
  }

  const normalized = url.toLowerCase();
  return normalized.endsWith(".mp4") || normalized.includes("/video/");
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "NA";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

export function IncidentReview({ alert, onNavigate, onBack, backLabel }: IncidentReviewProps) {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const goBack = () => (onBack ? onBack() : onNavigate("alerts"));
  const label = backLabel ?? t("common.back");

  const [appeal, setAppeal] = useState<Appeal | null>(null);
  const [loadingAppeal, setLoadingAppeal] = useState(false);
  const [appealDesc, setAppealDesc] = useState("");
  const [appealAttachment, setAppealAttachment] = useState("");
  const [submittingAppeal, setSubmittingAppeal] = useState(false);
  const [appealError, setAppealError] = useState<string | null>(null);

  useEffect(() => {
    if (!alert?.id) return;
    
    let cancelled = false;
    setLoadingAppeal(true);
    setAppeal(null);
    setAppealError(null);

    const loadAppeal = async () => {
      try {
        if (user?.role === "driver") {
          const myAppeals = await listMyAppeals();
          if (cancelled) return;
          const found = myAppeals.find(ap => ap.alertId === alert.id) || null;
          setAppeal(found);
        } else {
          const adminAppeals = await listAppealsAdmin();
          if (cancelled) return;
          const found = adminAppeals.find(ap => ap.alertId === alert.id) || null;
          setAppeal(found);
        }
      } catch (err) {
        console.error("Failed to load appeal details", err);
      } finally {
        if (!cancelled) setLoadingAppeal(false);
      }
    };

    void loadAppeal();
    return () => {
      cancelled = true;
    };
  }, [alert?.id, user?.role]);

  const handleSubmitAppeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!alert?.id) return;
    
    setSubmittingAppeal(true);
    setAppealError(null);
    try {
      const created = await createAppeal({
        alertId: alert.id,
        description: appealDesc.trim(),
        attachmentUrl: appealAttachment.trim()
      });
      setAppeal(created);
      setAppealDesc("");
      setAppealAttachment("");
    } catch (err: any) {
      setAppealError(err.message || "Failed to submit appeal");
    } finally {
      setSubmittingAppeal(false);
    }
  };
  
  if (!alert) {
    return (
      <div className="p-6 max-w-3xl mx-auto space-y-4">
        <div>
          <h2 className="text-lg font-bold text-primary tracking-tight">{t("incident.title")}</h2>
          <p className="text-xs text-secondary mt-1">No alert selected from backend feed.</p>
        </div>
        <button
          type="button"
          onClick={goBack}
          className="inline-flex items-center gap-1.5 bg-primary text-on-primary px-3 py-1.5 rounded-lg text-xs font-semibold"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          {label}
        </button>
      </div>
    );
  }

  const plateNumber = alert.vehicle?.plateNumber ?? alert.vehicleId ?? "Unknown";
  const driverName = alert.user?.name ?? "Unknown Driver";
  const alertTypeLabel = formatAlertTypeLabel(alert.alertType);

  return (
    <div className="p-6 max-w-7xl w-full mx-auto space-y-4 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-secondary mb-1 block">
            {t("incident.auditLog")}
          </span>
          <h2 className="text-xl font-bold text-primary tracking-tight leading-none">
            {t("incident.title")}: {alertTypeLabel}
          </h2>
        </div>
        <button
          type="button"
          onClick={goBack}
          className="flex items-center text-primary font-bold text-xs hover:translate-x-[-4px] transition-transform cursor-pointer"
        >
          <ArrowLeft className="mr-1.5 w-4 h-4" />
          {label}
        </button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Column: Driver, Vehicle, Timestamp, Severity details (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <section className="bg-surface-container-lowest p-4 rounded-xl ring-1 ring-outline-variant/15 shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-surface-container-low p-3 rounded-lg ring-1 ring-outline-variant/20">
                <p className="text-[9px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center">
                  {t("dashboard.driver")}
                </p>
                <div className="mt-2 flex items-center gap-3">
                  {alert.user?.avatarImageUrl ? (
                    <img
                      src={alert.user.avatarImageUrl}
                      alt={driverName}
                      className="w-14 h-14 rounded-md object-cover ring-1 ring-outline-variant/30 shadow-sm"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-md bg-primary text-on-primary flex items-center justify-center font-bold text-sm shadow-sm">
                      {initials(driverName)}
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-primary truncate">{driverName}</p>
                    <p className="text-[10px] text-secondary mt-0.5 truncate">{alert.user?.email ?? "No user email"}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-surface-container-low p-3 rounded-lg ring-1 ring-outline-variant/20">
                <p className="text-[9px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center">
                  {t("dashboard.vehicle")}
                </p>
                <div className="mt-2 flex items-center gap-3">
                  {alert.vehicle?.vehicleImageUrl ? (
                    <img
                      src={alert.vehicle.vehicleImageUrl}
                      alt={plateNumber}
                      className="w-14 h-14 rounded-md object-cover ring-1 ring-outline-variant/30 shadow-sm"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-md bg-surface-container-high text-secondary flex items-center justify-center text-[10px] font-semibold text-center px-1.5 shadow-sm">
                      No image
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-primary truncate">{plateNumber}</p>
                    <p className="text-[10px] text-secondary mt-0.5 truncate">
                      {alert.vehicle ? `${alert.vehicle.manufacturer} ${alert.vehicle.model}` : "No vehicle info"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-3 border-t border-surface-container-high">
              <div className="bg-surface-container-low p-3 rounded-lg">
                <p className="text-[9px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center">
                  {t("common.time")}
                </p>
                <p className="text-xs font-semibold text-primary">{formatTimestamp(alert.createdAt)}</p>
              </div>
              
              <div className="bg-surface-container-low p-3 rounded-lg">
                <p className="text-[9px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center">
                  {t("incident.geoLocation")}
                </p>
                <p className="text-xs font-semibold text-primary">{locationLabel(alert)}</p>
              </div>
            </div>
          </section>

          <section className="bg-primary text-white p-4 rounded-xl shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-4">
                <AlertOctagon className="w-6 h-6 text-white" />
                <span className="bg-error-container text-on-error-container px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest">
                  {severityLabel(alert.alertType)}
                </span>
              </div>
              <div className="space-y-2">
                <div>
                  <label className="text-[9px] font-bold opacity-70 uppercase tracking-wider">{t("incident.alertType")}</label>
                  <p className="text-base font-bold">{alertTypeLabel}</p>
                </div>
                <div>
                  <label className="text-[9px] font-bold opacity-70 uppercase tracking-wider">{t("incident.message")}</label>
                  <p className="text-xs font-medium text-white/90 mt-0.5 leading-relaxed">{alert.message}</p>
                </div>
              </div>
            </div>
            <div className="text-[10px] text-white/60 mt-4 border-t border-white/10 pt-2">ID: {alert.id}</div>
          </section>
        </div>

        {/* Right Column: Evidence Dossier (5 cols) */}
        <div className="lg:col-span-5 space-y-2.5">
          <h4 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5 pl-1">
            <Video className="w-4 h-4" />
            {t("incident.evidence")}
          </h4>

          {alert.evidenceUrl ? (
            <div className="rounded-xl overflow-hidden ring-1 ring-outline-variant/20 bg-surface-container-highest shadow-sm flex flex-col">
              <div className="w-full aspect-[4/3] bg-black flex items-center justify-center overflow-hidden">
                {isVideoEvidence(alert.evidenceUrl) ? (
                  <video className="w-full h-full object-contain" controls src={alert.evidenceUrl} />
                ) : (
                  <img className="w-full h-full object-contain" src={alert.evidenceUrl} alt="Alert evidence" />
                )}
              </div>
              <div className="px-3 py-2 text-[10px] text-secondary bg-surface-container-low border-t border-outline-variant/20 font-mono truncate">
                {alert.evidenceUrl}
              </div>
            </div>
          ) : (
            <div className="rounded-xl p-6 bg-surface-container-low text-secondary text-xs text-center border border-outline-variant/10 aspect-[4/3] flex flex-col items-center justify-center">
              {t("incident.noEvidence")}
            </div>
          )}

          {/* Appeal Case Section */}
          <div className="mt-4 pt-4 border-t border-outline-variant/20 flex flex-col gap-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5 pl-1">
              <AlertCircle className="w-4 h-4 text-primary" />
              {t("incident.appealTitle")}
            </h4>

            {loadingAppeal ? (
              <div className="bg-surface-container rounded-xl p-4 text-center text-xs text-secondary">
                {t("common.loading")}
              </div>
            ) : appeal ? (
              <div className="bg-surface-container rounded-xl p-4 flex flex-col gap-3 shadow-sm border border-outline-variant/10">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-secondary font-medium">{t("appeals.appealStatus")}</span>
                  <span className={`inline-flex items-center rounded px-2.5 py-0.5 text-[10px] font-bold uppercase ${
                    appeal.status === "APPROVED"
                      ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                      : appeal.status === "REJECTED"
                      ? "bg-error/10 text-error border border-error/20"
                      : "bg-amber-500/10 text-amber-600 border border-amber-500/20 animate-pulse"
                  }`}>
                    {appeal.status === "PENDING" ? t("appeals.pending") : appeal.status === "APPROVED" ? t("appeals.approved") : t("appeals.rejected")}
                  </span>
                </div>

                <div className="flex flex-col gap-1.5 border-t border-surface-container-high pt-2.5">
                  <span className="text-[10px] font-bold text-secondary">{t("appeals.driverNotes")}</span>
                  <p className="text-xs text-on-surface bg-surface-container-low p-2.5 rounded-lg border border-outline-variant/10 whitespace-pre-line leading-relaxed">
                    {appeal.description || <span className="italic opacity-55">{t("appeals.noDescription")}</span>}
                  </p>
                </div>

                {appeal.attachmentUrl && (
                  <div className="flex flex-col gap-1.5 border-t border-surface-container-high pt-2.5">
                    <span className="text-[10px] font-bold text-secondary">{t("appeals.attachment")}</span>
                    <a 
                      href={appeal.attachmentUrl} 
                      target="_blank" 
                      rel="noreferrer" 
                      className="inline-flex items-center gap-1.5 self-start px-2.5 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-container-highest transition-colors border border-outline-variant/30 text-[10px] font-bold uppercase text-primary cursor-pointer shadow-sm"
                    >
                      <Paperclip className="w-3.5 h-3.5" />
                      {t("appeals.viewAttachment")}
                    </a>
                  </div>
                )}

                {(appeal.status === "APPROVED" || appeal.status === "REJECTED") && appeal.adminNote && (
                  <div className="flex flex-col gap-1.5 border-t border-surface-container-high pt-2.5">
                    <span className="text-[10px] font-bold text-secondary">{t("appeals.adminNoteLabel")}</span>
                    <p className="text-xs text-on-surface bg-surface-container-low p-2.5 rounded-lg border border-outline-variant/10 whitespace-pre-line leading-relaxed">
                      {appeal.adminNote}
                    </p>
                  </div>
                )}
              </div>
            ) : user?.role === "driver" ? (
              <form onSubmit={handleSubmitAppeal} className="bg-surface-container rounded-xl p-4 flex flex-col gap-3 shadow-sm border border-outline-variant/10">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold text-secondary uppercase tracking-wider">{t("appeals.driverNotes")}</label>
                  <textarea
                    value={appealDesc}
                    onChange={(e) => setAppealDesc(e.target.value)}
                    placeholder={t("incident.appealDescPlaceholder")}
                    rows={3}
                    required
                    className="w-full rounded-lg border border-outline-variant/40 bg-surface px-3 py-2 text-xs text-primary outline-none focus:ring-2 focus:ring-primary/30 resize-none"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <ImageUploader 
                    label={t("incident.uploadProof")} 
                    currentUrl={appealAttachment} 
                    onUploadSuccess={(url) => setAppealAttachment(url)} 
                  />
                </div>

                {appealError && (
                  <div className="text-[10px] text-error font-semibold bg-error/5 p-2 rounded border border-error/15">
                    {appealError}
                  </div>
                )}

                <div className="flex justify-end mt-1">
                  <button
                    type="submit"
                    disabled={submittingAppeal}
                    className="inline-flex items-center gap-2 bg-primary text-on-primary text-[10px] font-bold uppercase px-3 py-2 rounded-lg hover:opacity-90 disabled:opacity-60 cursor-pointer shadow-sm"
                  >
                    <Send className="w-3.5 h-3.5" />
                    {submittingAppeal ? t("incident.submitting") : t("incident.submitAppeal")}
                  </button>
                </div>
              </form>
            ) : (
              <div className="bg-surface-container rounded-xl p-4 text-center text-xs text-secondary border border-outline-variant/10">
                {t("incident.noAppealFound")}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
