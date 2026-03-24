import { LayoutDashboard, Car, Users, AlertTriangle, Settings, HelpCircle, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  currentView: "dashboard" | "incident" | "alerts";
  onNavigate: (view: "dashboard" | "incident" | "alerts") => void;
}

export function Sidebar({ currentView, onNavigate }: SidebarProps) {
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
        <button className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded transition-all w-full text-left">
          <Car className="w-5 h-5" />
          <span className="text-sm font-medium">Vehicles</span>
        </button>
        <button className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded transition-all w-full text-left">
          <Users className="w-5 h-5" />
          <span className="text-sm font-medium">Drivers</span>
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
        <button className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded transition-all w-full text-left">
          <LogOut className="w-5 h-5" />
          <span className="text-sm font-medium">Logout</span>
        </button>
      </div>
    </aside>
  );
}
