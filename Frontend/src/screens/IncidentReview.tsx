import { ArrowLeft, AlertOctagon, CalendarDays, Car, MapPin, UserRound, Video } from "lucide-react";
import { Alert, formatAlertTypeLabel, getAlertSeverity } from "@/types/alert";

interface IncidentReviewProps {
  alert: Alert | null;
  onNavigate: (view: "dashboard" | "incident" | "alerts") => void;
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

export function IncidentReview({ alert, onNavigate }: IncidentReviewProps) {
  if (!alert) {
    return (
      <div className="p-10 max-w-5xl mx-auto space-y-6">
        <div>
          <h2 className="text-3xl font-black text-primary tracking-tight">Incident Review</h2>
          <p className="text-secondary mt-2">No alert selected from backend feed.</p>
        </div>
        <button
          type="button"
          onClick={() => onNavigate("alerts")}
          className="inline-flex items-center gap-2 bg-primary text-on-primary px-4 py-2 rounded-lg font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          Back To Alerts
        </button>
      </div>
    );
  }

  const plateNumber = alert.vehicle?.plateNumber ?? alert.vehicleId ?? "Unknown";
  const driverName = alert.user?.name ?? "Unknown Driver";
  const alertTypeLabel = formatAlertTypeLabel(alert.alertType);

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface-variant mb-2 block">
            Incident Audit Log
          </span>
          <h2 className="text-4xl font-black text-primary tracking-tight leading-none">Incident Review: {alertTypeLabel}</h2>
        </div>
        <button
          type="button"
          onClick={() => onNavigate("alerts")}
          className="flex items-center text-primary font-bold text-sm hover:translate-x-[-4px] transition-transform"
        >
          <ArrowLeft className="mr-2 w-5 h-5" />
          Back to Alerts
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <section className="lg:col-span-7 bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-surface-container-low p-4 rounded-lg ring-1 ring-outline-variant/20">
              <p className="text-[10px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center gap-2">
                <UserRound className="w-4 h-4" /> Driver
              </p>
              <div className="mt-3 flex items-center gap-4">
                {alert.user?.avatarImageUrl ? (
                  <img
                    src={alert.user.avatarImageUrl}
                    alt={driverName}
                    className="w-24 h-24 rounded-md object-cover ring-1 ring-outline-variant/30 shadow-sm"
                  />
                ) : (
                  <div className="w-24 h-24 rounded-md bg-primary text-on-primary flex items-center justify-center font-black text-xl shadow-sm">
                    {initials(driverName)}
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-xl font-bold text-primary truncate">{driverName}</p>
                  <p className="text-xs text-secondary mt-1 truncate">{alert.user?.email ?? "No user email"}</p>
                </div>
              </div>
            </div>
            <div className="bg-surface-container-low p-4 rounded-lg ring-1 ring-outline-variant/20">
              <p className="text-[10px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center gap-2">
                <Car className="w-4 h-4" /> Vehicle
              </p>
              <div className="mt-3 flex items-center gap-4">
                {alert.vehicle?.vehicleImageUrl ? (
                  <img
                    src={alert.vehicle.vehicleImageUrl}
                    alt={plateNumber}
                    className="w-24 h-24 rounded-md object-cover ring-1 ring-outline-variant/30 shadow-sm"
                  />
                ) : (
                  <div className="w-24 h-24 rounded-md bg-surface-container-high text-secondary flex items-center justify-center text-xs font-semibold text-center px-2 shadow-sm">
                    No vehicle image
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-xl font-bold text-primary truncate">{plateNumber}</p>
                  <p className="text-xs text-secondary mt-1 truncate">
                    {alert.vehicle ? `${alert.vehicle.manufacturer} ${alert.vehicle.model}` : "No vehicle info"}
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-surface-container-low p-4 rounded-lg">
              <p className="text-[10px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center gap-2">
                <CalendarDays className="w-4 h-4" /> Timestamp
              </p>
              <p className="text-sm font-semibold text-primary">{formatTimestamp(alert.createdAt)}</p>
            </div>
            <div className="bg-surface-container-low p-4 rounded-lg">
              <p className="text-[10px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center gap-2">
                <MapPin className="w-4 h-4" /> Geo-Location
              </p>
              <p className="text-sm font-semibold text-primary">{locationLabel(alert)}</p>
            </div>
          </div>
        </section>

        <section className="lg:col-span-5 bg-primary text-white p-6 rounded-xl shadow-sm">
          <div className="flex justify-between items-start mb-5">
            <AlertOctagon className="w-8 h-8 text-white" />
            <span className="bg-error-container text-on-error-container px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
              {severityLabel(alert.alertType)}
            </span>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-[10px] font-bold opacity-70 uppercase tracking-widest">Alert Type</label>
              <p className="text-2xl font-bold">{alertTypeLabel}</p>
            </div>
            <div>
              <label className="text-[10px] font-bold opacity-70 uppercase tracking-widest">Message</label>
              <p className="text-sm font-medium text-white/90 mt-1">{alert.message}</p>
            </div>
            <div className="text-xs text-white/80">Alert ID: {alert.id}</div>
          </div>
        </section>
      </div>

      <section className="space-y-4">
        <h4 className="text-sm font-black text-primary uppercase tracking-widest flex items-center gap-2">
          <Video className="w-5 h-5" />
          Evidence Dossier
        </h4>

        {alert.evidenceUrl ? (
          <div className="rounded-xl overflow-hidden ring-1 ring-outline-variant/20 bg-surface-container-highest shadow-sm">
            {isVideoEvidence(alert.evidenceUrl) ? (
              <video className="w-full max-h-[520px] bg-black" controls src={alert.evidenceUrl} />
            ) : (
              <img className="w-full max-h-[520px] object-cover" src={alert.evidenceUrl} alt="Alert evidence" />
            )}
            <div className="px-4 py-3 text-xs text-secondary bg-surface-container-low border-t border-outline-variant/20">
              {alert.evidenceUrl}
            </div>
          </div>
        ) : (
          <div className="rounded-xl p-8 bg-surface-container-low text-secondary text-sm">No evidence URL available.</div>
        )}
      </section>
    </div>
  );
}
