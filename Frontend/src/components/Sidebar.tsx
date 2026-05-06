import { useState, useEffect } from "react";
import { LayoutDashboard, Car, Users, AlertTriangle, Settings, HelpCircle, LogOut, Monitor, ChevronDown, ChevronRight, Wifi, WifiOff, MessageSquareWarning, Package } from "lucide-react";
import { cn } from "@/lib/utils";
import { AppView } from "@/App";
import { useAuth } from "@/auth/AuthContext";
import { useNavigate } from "react-router-dom";
import { getVehicles } from "@/api/vehicles";
import type { Vehicle } from "@/types/vehicle";

interface Device {
  id: string;
  label: string;
  online: boolean;
}

interface SidebarProps {
  currentView: AppView;
  onNavigate: (view: AppView) => void;
  onOpenMonitor?: (deviceId: string) => void;
}

const WS_BASE = (import.meta.env.VITE_WS_ALERTS_URL as string | undefined)
  ? (import.meta.env.VITE_WS_ALERTS_URL as string).replace(/\/alerts$/, "")
  : "ws://localhost:8000/api/v1/ws";

export function Sidebar({ currentView, onNavigate, onOpenMonitor }: SidebarProps) {
  const [monitorOpen, setMonitorOpen] = useState(false);
  const [vehiclesOpen, setVehiclesOpen] = useState(false);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [devices, setDevices] = useState<Device[]>([
    { id: "esp32-cam", label: "ESP32-CAM", online: false },
  ]);
  const { logout } = useAuth();
  const navigate = useNavigate();
  // Lightweight status probe: connect to /ws/frontend and listen for pong
  useEffect(() => {
    if (currentView === "monitor") {
      setMonitorOpen(true);
    }
    if (currentView === "vehicles") {
      setVehiclesOpen(true);
    }
  }, [currentView]);

  useEffect(() => {
    if (vehiclesOpen && vehicles.length === 0) {
      getVehicles(10).then(setVehicles).catch(() => {});
    }
  }, [vehiclesOpen, vehicles.length]);

  useEffect(() => {
    if (!monitorOpen) return;

    let ws: WebSocket | null = null;
    let pingInterval: ReturnType<typeof setInterval> | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      ws = new WebSocket(`${WS_BASE}/frontend`);

      ws.addEventListener("open", () => {
        ws!.send(JSON.stringify({ type: "ping" }));
        pingInterval = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, 8000);
      });

      ws.addEventListener("message", (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === "pong") {
            const deviceId: string = msg.device ?? "esp32-cam";
            setDevices([
              { id: deviceId, label: deviceId.toUpperCase(), online: !!msg.camera },
            ]);
          }
        } catch { /* ignore */ }
      });

      ws.addEventListener("close", () => {
        if (pingInterval) clearInterval(pingInterval);
        reconnectTimeout = setTimeout(connect, 4000);
      });

      ws.addEventListener("error", () => {
        ws?.close();
      });
    };

    connect();

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      ws?.close();
    };
  }, [monitorOpen]);

  const handleMonitorClick = () => {
    setMonitorOpen((prev: boolean) => !prev);
    setVehiclesOpen(false);
    onNavigate("monitor");
  };

  const handleVehiclesClick = () => {
    setVehiclesOpen((prev: boolean) => !prev);
    setMonitorOpen(false);
    onNavigate("vehicles");
  };

  const handleDeviceSelect = (deviceId: string) => {
    onOpenMonitor?.(deviceId);
    onNavigate("monitor");
  };

  return (
    <aside className="fixed left-0 top-0 h-full flex flex-col p-4 gap-2 border-r border-surface-container-high bg-surface-container-lowest w-64 z-50">
      <div className="mb-8 px-2 py-2">
        <svg viewBox="0 0 500 120" className="h-12 w-auto" xmlns="http://www.w3.org/2000/svg">
          <g transform="translate(10, 10)">
            {/* Shield Outline */}
            <path d="M 10 15 Q 50 0 90 15 L 90 50 C 90 80 50 100 50 100 C 50 100 10 80 10 50 Z" fill="none" stroke="#1a365d" strokeWidth="8" strokeLinejoin="round" />
            
            {/* Compass Star */}
            <g transform="translate(50, 35) scale(0.8)">
              <path d="M 0 -25 L 5 -5 L 25 0 L 5 5 L 0 25 L -5 5 L -25 0 L -5 -5 Z" fill="#a18042" />
              <path d="M 0 -25 L 5 -5 L 0 0 Z" fill="#1a365d" />
              <path d="M 25 0 L 5 5 L 0 0 Z" fill="#1a365d" />
              <path d="M 0 25 L -5 5 L 0 0 Z" fill="#1a365d" />
              <path d="M -25 0 L -5 -5 L 0 0 Z" fill="#1a365d" />
            </g>

            {/* Road */}
            <path d="M 15 80 C 30 50 60 40 95 35 L 95 55 C 60 60 40 70 25 95 Z" fill="#4a5568" />
            {/* Dashed line on road */}
            <path d="M 22 85 C 35 60 60 50 90 45" fill="none" stroke="#ffffff" strokeWidth="2" strokeDasharray="6,4" />
            
            {/* Graph bars */}
            <g transform="translate(60, 65) scale(0.6)">
              <rect x="0" y="10" width="3" height="10" fill="#a18042" />
              <rect x="5" y="5" width="3" height="15" fill="#a18042" />
              <rect x="10" y="0" width="3" height="20" fill="#a18042" />
              <rect x="15" y="8" width="3" height="12" fill="#a18042" />
              <rect x="20" y="2" width="3" height="18" fill="#a18042" />
            </g>
          </g>
          
          {/* Text */}
          <text x="120" y="65" fontFamily="Inter, sans-serif" fontSize="48" fontWeight="800" fill="#1a365d">Road<tspan fill="#4a5568">Sentinel</tspan></text>
          <text x="125" y="90" fontFamily="Inter, sans-serif" fontSize="14" fontWeight="700" fill="#4a5568" letterSpacing="1.5">ENTERPRISE FLEET INTELLIGENCE</text>
        </svg>
      </div>
      <nav className="flex-1 flex flex-col gap-1">
        <button
          onClick={() => onNavigate("dashboard")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left",
            currentView === "dashboard"
              ? "text-primary bg-surface-container font-bold"
              : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <LayoutDashboard className="w-5 h-5" />
          <span className="text-sm">Dashboard</span>
        </button>
        <button
          onClick={handleVehiclesClick}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left",
            currentView === "vehicles"
              ? "text-primary bg-surface-container font-bold"
              : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <Car className="w-5 h-5" />
          <span className="text-sm flex-1">Vehicles</span>
          {vehiclesOpen ? (
            <ChevronDown className="w-4 h-4 opacity-50" />
          ) : (
            <ChevronRight className="w-4 h-4 opacity-50" />
          )}
        </button>

        {vehiclesOpen && (
          <div className="ml-4 pl-3 border-l-2 border-surface-container-high flex flex-col gap-0.5 py-1 transition-all">
            {vehicles.length === 0 ? (
              <span className="text-[10px] text-secondary px-3 py-2 italic">No vehicles found</span>
            ) : (
              vehicles.slice(0, 5).map((v) => (
                <button
                  key={v.id}
                  onClick={() => onNavigate("vehicles")}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-surface-container-low transition-all w-full text-left group"
                >
                  <Package className="w-3.5 h-3.5 text-secondary opacity-50" />
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-bold text-primary truncate">{v.plateNumber}</span>
                    <span className="text-[10px] text-secondary truncate">{v.manufacturer} {v.model}</span>
                  </div>
                </button>
              ))
            )}
            {vehicles.length > 5 && (
              <button
                onClick={() => onNavigate("vehicles")}
                className="text-[10px] font-bold text-primary px-3 py-1 hover:underline text-left"
              >
                View all vehicles...
              </button>
            )}
          </div>
        )}
        <button
          onClick={() => onNavigate("drivers")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left",
            currentView === "drivers"
              ? "text-primary bg-surface-container font-bold"
              : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <Users className="w-5 h-5" />
          <span className="text-sm">Drivers</span>
        </button>
        <button
          onClick={() => onNavigate("alerts")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left",
            currentView === "alerts"
              ? "text-primary bg-surface-container font-bold"
              : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <AlertTriangle className={cn("w-5 h-5", currentView === "alerts" && "fill-current")} />
          <span className="text-sm">Alerts</span>
        </button>
        <button
          onClick={() => onNavigate("appeals")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left",
            currentView === "appeals"
              ? "text-primary bg-surface-container font-bold"
              : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <MessageSquareWarning className="w-5 h-5" />
          <span className="text-sm">Appeals</span>
        </button>

        {/* ── Monitor nav item ──────────────────────────────────────────── */}
        <button
          onClick={handleMonitorClick}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left",
            currentView === "monitor"
              ? "text-primary bg-surface-container font-bold"
              : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <Monitor className="w-5 h-5" />
          <span className="text-sm flex-1">Monitor</span>
          {monitorOpen ? (
            <ChevronDown className="w-4 h-4 opacity-50" />
          ) : (
            <ChevronRight className="w-4 h-4 opacity-50" />
          )}
        </button>

        {/* ── Device list (collapsible) ─────────────────────────────────── */}
        {monitorOpen && (
          <div className="ml-4 pl-3 border-l-2 border-surface-container-high flex flex-col gap-0.5 py-1 transition-all">
            {devices.map((device) => (
              <button
                key={device.id}
                onClick={() => handleDeviceSelect(device.id)}
                className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-surface-container-low transition-all w-full text-left group"
              >
                {device.online ? (
                  <span className="relative flex h-2 w-2 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </span>
                ) : (
                  <span className="h-2 w-2 rounded-full bg-outline/40 shrink-0" />
                )}
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-bold text-primary truncate">{device.label}</span>
                  <span className="text-[10px] text-secondary">
                    {device.online ? (
                      <span className="flex items-center gap-1 text-emerald-600">
                        <Wifi className="w-2.5 h-2.5" /> Live
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-outline">
                        <WifiOff className="w-2.5 h-2.5" /> Offline
                      </span>
                    )}
                  </span>
                </div>
                <span className="ml-auto text-[9px] font-bold text-primary opacity-0 group-hover:opacity-100 transition-opacity uppercase tracking-wide">
                  Connect
                </span>
              </button>
            ))}
          </div>
        )}

        <button className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded transition-all w-full text-left">
          <Settings className="w-5 h-5" />
          <span className="text-sm font-medium">Settings</span>
        </button>
      </nav>
      <div className="mt-auto flex flex-col gap-1 pt-4 border-t border-surface-container-high">
        {currentView === "incident" && (
          <button className="mx-4 mb-6 py-3 px-4 bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 transition-all text-xs">
            Generate Report
          </button>
        )}
        <button className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded transition-all w-full text-left">
          <HelpCircle className="w-5 h-5" />
          <span className="text-sm font-medium">Support</span>
        </button>
        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
          className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded transition-all w-full text-left"
        >
          <LogOut className="w-5 h-5" />
          <span className="text-sm font-medium">Logout</span>
        </button>
      </div>
    </aside>
  );
}
