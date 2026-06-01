import { useState, useEffect } from "react";
import { LayoutDashboard, Car, Users, AlertTriangle, Settings, HelpCircle, LogOut, Monitor, ChevronDown, ChevronRight, Wifi, WifiOff, MessageSquareWarning, Package } from "lucide-react";
import { cn } from "@/lib/utils";
import { AppView } from "@/App";
import { useAuth } from "@/auth/AuthContext";
import { useNavigate } from "react-router-dom";
import { Logo } from "@/components/Logo";

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
  }, [currentView]);

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
    onNavigate("monitor");
  };

  const handleVehiclesClick = () => {
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
        <Logo className="h-10 w-auto" />
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
        </button>
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
