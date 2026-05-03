import { UserRound, Video, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";

type Tab = "profile" | "violations";

export function DriverSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, user } = useAuth();

  const tab: Tab = location.pathname.includes("/violations") ? "violations" : "profile";

  return (
    <aside className="fixed left-0 top-0 h-full flex flex-col p-4 gap-2 border-r border-surface-container-high bg-surface-container-lowest w-64 z-50">
      <div className="mb-6 px-2 py-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-secondary">RoadSentinel</p>
        <p className="text-lg font-black text-primary leading-tight">Driver Portal</p>
        <p className="text-xs text-secondary mt-1 truncate">{user?.email}</p>
      </div>
      <nav className="flex-1 flex flex-col gap-1">
        <button
          type="button"
          onClick={() => navigate("/driver")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left text-sm",
            tab === "profile" ? "text-primary bg-surface-container font-bold" : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <UserRound className="w-5 h-5" />
          My Profile
        </button>
        <button
          type="button"
          onClick={() => navigate("/driver/violations")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left text-sm",
            tab === "violations" ? "text-primary bg-surface-container font-bold" : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <Video className="w-5 h-5" />
          Violation Evidence
        </button>
      </nav>
      <div className="mt-auto pt-4 border-t border-surface-container-high">
        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
          className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded w-full text-left text-sm font-medium"
        >
          <LogOut className="w-5 h-5" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}