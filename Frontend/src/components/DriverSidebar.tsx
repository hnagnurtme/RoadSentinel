import { UserRound, Video, LogOut, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { Logo } from "@/components/Logo";
import { useLanguage } from "@/i18n/LanguageContext";

type Tab = "profile" | "violations" | "sessions";

export function DriverSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, user } = useAuth();
  const { language, setLanguage, t } = useLanguage();

  const tab: Tab = location.pathname.includes("/violations") 
    ? "violations" 
    : location.pathname.includes("/sessions") 
      ? "sessions" 
      : "profile";

  const displayName = user
    ? user.name || [user.name__given, user.name__family].filter(Boolean).join(" ") || user.email
    : "Driver";

  return (
    <aside className="fixed left-0 top-0 h-full flex flex-col p-4 gap-2 border-r border-surface-container-high bg-surface-container-lowest w-64 z-50">
      <div className="mb-8 px-2 py-2">
        <Logo className="h-10 w-auto" />
      </div>
      <nav className="flex-1 flex flex-col gap-1">
        <button
          type="button"
          onClick={() => navigate("/driver")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left text-sm cursor-pointer",
            tab === "profile" ? "text-primary bg-surface-container font-bold" : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <UserRound className="w-5 h-5" />
          <span>{t("sidebar.profile")}</span>
        </button>
        <button
          type="button"
          onClick={() => navigate("/driver/sessions")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left text-sm cursor-pointer",
            tab === "sessions" ? "text-primary bg-surface-container font-bold" : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <Clock className="w-5 h-5" />
          <span>{t("sidebar.timekeeping")}</span>
        </button>
        <button
          type="button"
          onClick={() => navigate("/driver/violations")}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded transition-all w-full text-left text-sm cursor-pointer",
            tab === "violations" ? "text-primary bg-surface-container font-bold" : "text-secondary hover:bg-surface-container-low font-medium"
          )}
        >
          <Video className="w-5 h-5" />
          <span>{t("sidebar.violations")}</span>
        </button>
      </nav>
      <div className="mt-auto flex flex-col gap-2 pt-4 border-t border-surface-container-high">
        {/* Driver Profile Summary Card */}
        <div className="flex items-center gap-3 p-3 mb-2 bg-surface-container-low rounded-xl border border-surface-container-high">
          <div className="w-10 h-10 rounded-full bg-surface-container border border-surface-container-high flex items-center justify-center overflow-hidden shrink-0">
            {user?.avatar_image_url ? (
              <img src={user.avatar_image_url} alt="" className="w-full h-full object-cover" />
            ) : (
              <UserRound className="w-5 h-5 text-primary" />
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-primary leading-tight truncate">{displayName}</p>
            <p className="text-[10px] text-secondary font-medium mt-0.5">
              {language === "en" ? "Driver Portal" : "Cổng thông tin tài xế"}
            </p>
          </div>
        </div>

        {/* Language Switcher */}
        <div className="flex items-center justify-between px-4 py-2 text-[11px] font-semibold text-secondary">
          <span>Language / Ngôn ngữ</span>
          <div className="flex gap-1 bg-surface-container rounded-lg p-0.5 border border-outline-variant/10">
            <button
              onClick={() => setLanguage("en")}
              className={cn(
                "px-2 py-0.5 rounded text-[9px] font-bold uppercase transition-all cursor-pointer",
                language === "en" ? "bg-primary text-on-primary shadow-sm" : "hover:text-primary"
              )}
            >
              EN
            </button>
            <button
              onClick={() => setLanguage("vi")}
              className={cn(
                "px-2 py-0.5 rounded text-[9px] font-bold uppercase transition-all cursor-pointer",
                language === "vi" ? "bg-primary text-on-primary shadow-sm" : "hover:text-primary"
              )}
            >
              VI
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
          className="flex items-center gap-3 px-4 py-2.5 text-secondary hover:bg-surface-container-low rounded w-full text-left text-sm font-medium cursor-pointer"
        >
          <LogOut className="w-5 h-5" />
          <span>{t("sidebar.logout")}</span>
        </button>
      </div>
    </aside>
  );
}