import { AlertTriangle, LocateFixed, Navigation } from "lucide-react";
import { useMemo, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import { Alert, formatAlertTypeLabel, getAlertSeverity } from "@/types/alert";

interface MapComponentProps {
  alerts: Alert[];
  onReviewAlert: (alert: Alert) => void;
}

const DANANG_CENTER: LatLngExpression = [16.0544, 108.2022];

function markerColor(alertType: string): string {
  const severity = getAlertSeverity(alertType);

  if (severity === "critical") {
    return "#ba1a1a";
  }

  if (severity === "moderate") {
    return "#f59e0b";
  }

  return "#2563eb";
}

function validMapAlerts(alerts: Alert[]): Alert[] {
  return alerts.filter((alert) => alert.latitude != null && alert.longitude != null);
}

function MapActions() {
  const map = useMap();
  const [isLocating, setIsLocating] = useState(false);

  const handleLocate = () => {
    if (!navigator.geolocation) {
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        map.setView([position.coords.latitude, position.coords.longitude], 14);
        setIsLocating(false);
      },
      () => {
        setIsLocating(false);
      },
    );
  };

  return (
    <div className="absolute z-[500] right-4 bottom-4 flex flex-col gap-2">
      <button
        type="button"
        onClick={handleLocate}
        className="w-10 h-10 rounded-lg bg-white/95 border border-outline-variant/40 text-primary shadow-md hover:bg-white transition-colors flex items-center justify-center"
        title="Center to current location"
      >
        <LocateFixed className={`w-4 h-4 ${isLocating ? "animate-pulse" : ""}`} />
      </button>
      <button
        type="button"
        onClick={() => map.zoomIn()}
        className="w-10 h-10 rounded-lg bg-white/95 border border-outline-variant/40 text-primary shadow-md hover:bg-white transition-colors text-lg font-bold"
        title="Zoom in"
      >
        +
      </button>
      <button
        type="button"
        onClick={() => map.zoomOut()}
        className="w-10 h-10 rounded-lg bg-white/95 border border-outline-variant/40 text-primary shadow-md hover:bg-white transition-colors text-lg font-bold"
        title="Zoom out"
      >
        -
      </button>
    </div>
  );
}

export function MapComponent({ alerts, onReviewAlert }: MapComponentProps) {
  const mapAlerts = useMemo(() => validMapAlerts(alerts), [alerts]);

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-outline-variant/30 shadow-lg relative">
      <MapContainer center={DANANG_CENTER} zoom={12} className="w-full h-full" zoomControl={false}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {mapAlerts.map((alert) => (
          <CircleMarker
            key={alert.id}
            center={[alert.latitude as number, alert.longitude as number]}
            radius={8}
            pathOptions={{
              color: "#ffffff",
              weight: 2,
              fillColor: markerColor(alert.alertType),
              fillOpacity: 0.95,
            }}
            eventHandlers={{
              click: () => onReviewAlert(alert),
            }}
          >
            <Popup>
              <div className="space-y-2 min-w-52">
                <p className="text-sm font-bold text-primary leading-tight">{alert.message}</p>
                <p className="text-[11px] font-semibold text-secondary uppercase tracking-wide">
                  {formatAlertTypeLabel(alert.alertType)}
                </p>
                <p className="text-xs text-secondary">{alert.user?.name ?? "Unknown Driver"}</p>
                <button
                  type="button"
                  onClick={() => onReviewAlert(alert)}
                  className="w-full mt-1 bg-primary text-on-primary text-xs font-bold rounded-md px-3 py-2 hover:opacity-90"
                >
                  Review Incident
                </button>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        <MapActions />
      </MapContainer>

      <div className="absolute z-[500] left-4 top-4 bg-white/95 backdrop-blur rounded-xl border border-outline-variant/30 shadow-md px-4 py-3">
        <h3 className="text-[11px] font-black uppercase tracking-[0.16em] text-primary flex items-center gap-2">
          <Navigation className="w-4 h-4" />
          Live Map - External Tiles
        </h3>
        <p className="text-xs text-secondary mt-1">Source: OpenStreetMap API</p>
      </div>

      <div className="absolute z-[500] left-4 bottom-4 bg-white/95 backdrop-blur rounded-lg border border-outline-variant/30 shadow-md px-4 py-3 flex items-center gap-3">
        <AlertTriangle className="w-4 h-4 text-error" />
        <div>
          <p className="text-[10px] font-black uppercase tracking-widest text-secondary">Alerts With GPS</p>
          <p className="text-sm font-bold text-primary">{mapAlerts.length}</p>
        </div>
      </div>
    </div>
  );
}
