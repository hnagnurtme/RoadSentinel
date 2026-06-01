import { Search, Bell, User } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { useLanguage } from "@/i18n/LanguageContext";

export function DriverHeader() {
  const { user } = useAuth();
  const { t, language } = useLanguage();
  
  const displayName = user
    ? user.name || [user.name__given, user.name__family].filter(Boolean).join(" ") || user.email
    : "Driver";

  return (
    <header className="sticky top-0 z-40 bg-surface-container-lowest border-b border-surface-container-high shadow-sm px-10 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8 flex-1">
        <div className="relative max-w-md w-full ml-4">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
          <input
            className="w-full pl-11 pr-4 py-2.5 bg-surface-container-low/80 border border-surface-container-high rounded-xl text-sm placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-primary/10"
            placeholder={t("common.search")}
            type="search"
          />
        </div>
      </div>
      <div className="flex items-center gap-3.5 pl-6 border-l border-surface-container-high">
        <button type="button" className="p-2 hover:bg-surface-container-low rounded-lg cursor-pointer">
          <Bell className="text-secondary w-5 h-5" />
        </button>
        <div className="text-right">
          <p className="text-sm font-bold text-primary leading-tight">{displayName}</p>
          <p className="text-[11px] text-secondary font-medium">
            {language === "en" ? "Driver Portal" : "Cổng thông tin tài xế"}
          </p>
        </div>
        <div className="w-10 h-10 rounded-full bg-surface-container-low border border-surface-container-high flex items-center justify-center overflow-hidden shrink-0">
          {user?.avatar_image_url ? (
            <img src={user.avatar_image_url} alt="" className="w-full h-full object-cover" />
          ) : (
            <User className="w-6 h-6 text-primary" />
          )}
        </div>
      </div>
    </header>
  );
}