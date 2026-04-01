import { useEffect, useRef } from "react";
import { List } from "lucide-react";
import { Alert, formatAlertTypeLabel, getAlertSeverity } from "@/types/alert";

interface RealtimeAlertsPanelProps {
  alerts: Alert[];
  newAlertIds: Set<string>;
  onViewIncident: (alert: Alert) => void;
}

function relativeTimeLabel(createdAt: string | null): string {
  if (!createdAt) {
    return "n/a";
  }

  const diffMs = Date.now() - new Date(createdAt).getTime();
  const diffMins = Math.max(1, Math.floor(diffMs / 60000));

  if (diffMins < 60) {
    return `${diffMins}m`;
  }

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) {
    return `${diffHours}h`;
  }

  return `${Math.floor(diffHours / 24)}d`;
}

export function RealtimeAlertsPanel({ alerts, newAlertIds, onViewIncident }: RealtimeAlertsPanelProps) {
  const previousNewAlertIdsRef = useRef<Set<string>>(new Set());
  const audioContextRef = useRef<AudioContext | null>(null);

  const playCriticalAlertSound = () => {
    try {
      const AudioContextConstructor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextConstructor) {
        return;
      }

      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContextConstructor();
      }

      const context = audioContextRef.current;
      if (context.state === "suspended") {
        void context.resume();
      }

      const now = context.currentTime;
      const oscillator = context.createOscillator();
      const gainNode = context.createGain();

      oscillator.type = "square";
      oscillator.frequency.setValueAtTime(880, now);
      oscillator.frequency.exponentialRampToValueAtTime(660, now + 0.12);

      gainNode.gain.setValueAtTime(0.0001, now);
      gainNode.gain.exponentialRampToValueAtTime(0.08, now + 0.02);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);

      oscillator.connect(gainNode);
      gainNode.connect(context.destination);

      oscillator.start(now);
      oscillator.stop(now + 0.2);
    } catch {
      // Ignore audio failures (for example autoplay restrictions).
    }
  };

  useEffect(() => {
    return () => {
      if (audioContextRef.current) {
        void audioContextRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    const previousIds = previousNewAlertIdsRef.current;
    let shouldPlayCriticalBeep = false;

    for (const alert of alerts) {
      if (!newAlertIds.has(alert.id) || previousIds.has(alert.id)) {
        continue;
      }

      if (getAlertSeverity(alert.alertType) === "critical") {
        shouldPlayCriticalBeep = true;
        break;
      }
    }

    if (shouldPlayCriticalBeep) {
      playCriticalAlertSound();
    }

    previousNewAlertIdsRef.current = new Set(newAlertIds);
  }, [alerts, newAlertIds]);

  return (
    <div className="lg:col-span-3 flex flex-col rounded-xl shadow-lg overflow-hidden bg-primary text-on-primary p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <List className="text-on-primary w-6 h-6" />
          <h3 className="text-xl font-bold tracking-tight">Real-time Alerts</h3>
        </div>
        <span className="live-alert-badge">LIVE</span>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
        {alerts.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center text-on-primary/70 text-sm">
            No alerts yet. Waiting for backend events...
          </div>
        ) : (
          alerts.slice(0, 12).map((alert, index) => (
            <div
              key={alert.id}
              className={`flex items-center gap-3 py-2 border-b border-on-primary/10 cursor-pointer hover:bg-on-primary/5 transition-colors rounded px-2 -mx-2 ${
                newAlertIds.has(alert.id) ? "alert-flash-on-dark" : ""
              }`}
              onClick={() => onViewIncident(alert)}
            >
              <div className="flex-shrink-0 w-6 text-[11px] font-bold text-on-primary/40">
                {String(index + 1).padStart(2, "0")}
              </div>
              <div className="flex-1 min-w-0 space-y-1">
                <p className="text-xs font-medium text-on-primary/90 truncate">{alert.message}</p>
                <p className="text-[10px] font-bold uppercase tracking-wide text-on-primary/60">
                  {formatAlertTypeLabel(alert.alertType)}
                </p>
                {(alert.user?.name || alert.vehicle?.plateNumber) && (
                  <p className="text-[10px] font-semibold text-on-primary/50 truncate">
                    {[alert.user?.name, alert.vehicle?.plateNumber].filter(Boolean).join(" • ")}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {newAlertIds.has(alert.id) && <span className="new-alert-badge">NEW</span>}
                <span className="text-[9px] text-on-primary/40 whitespace-nowrap">{relativeTimeLabel(alert.createdAt)}</span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-4">
        <button
          type="button"
          className="w-full py-3.5 bg-surface-container-lowest text-primary text-sm font-bold rounded-lg hover:bg-surface-container-low transition-colors"
        >
          VIEW ALL ACTIVITY
        </button>
      </div>
    </div>
  );
}
