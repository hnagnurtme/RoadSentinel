import { Search, Bell, Mail, User } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-40 bg-surface-container-lowest border-b border-surface-container-high shadow-sm px-10 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8 flex-1">
        <div className="relative max-w-md w-full ml-4">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
          <input
            className="w-full pl-11 pr-4 py-2.5 bg-surface-container-low/80 border border-surface-container-high rounded-xl text-sm placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-primary/10 focus:border-primary/20 transition-all font-normal"
            placeholder="Search assets, incidents or drivers..."
            type="text"
          />
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 mr-2">
          <button className="relative p-2 hover:bg-surface-container-low rounded-lg transition-colors group">
            <Bell className="text-secondary group-hover:text-primary w-5 h-5" />
            <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full border-2 border-surface-container-lowest"></span>
          </button>
          <button className="p-2 hover:bg-surface-container-low rounded-lg transition-colors group">
            <Mail className="text-secondary group-hover:text-primary w-5 h-5" />
          </button>
        </div>
        <div className="flex items-center gap-3.5 pl-6 border-l border-surface-container-high">
          <div className="text-right flex flex-col">
            <p className="text-sm font-bold text-primary leading-tight">Chief Safety Officer</p>
            <p className="text-[11px] text-secondary font-medium leading-tight">Global Fleet Operations</p>
          </div>
          <div className="w-10 h-10 rounded-full bg-surface-container-low border border-surface-container-high flex items-center justify-center overflow-hidden cursor-pointer hover:border-primary/30 transition-colors">
            <User className="w-6 h-6 text-primary fill-current" />
          </div>
        </div>
      </div>
    </header>
  );
}
