import React from "react";
import { Activity } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";

interface LoadingRadarProps {
  message?: string;
  minHeight?: string;
  title?: string;
}

export function LoadingRadar({
  message,
  minHeight = "min-h-[75vh]",
  title = "RoadSentinel"
}: LoadingRadarProps) {
  const { language } = useLanguage();
  const displayMessage = message || (language === "en" ? "Retrieving Fleet Analytics" : "Đang tải dữ liệu đội xe");

  return (
    <div className={`w-full flex flex-col items-center justify-center p-8 relative overflow-hidden ${minHeight}`}>
      {/* Ambient premium background glows */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute top-1/3 left-1/4 w-72 h-72 bg-secondary/5 rounded-full blur-3xl animate-pulse" />

      <div className="relative z-10 flex flex-col items-center max-w-sm text-center">
        {/* Main Visual: Glowing Scanner/Radar Ring */}
        <div className="relative w-24 h-24 mb-8 flex items-center justify-center">
          {/* Outer pulsing ring */}
          <div className="absolute inset-0 rounded-full border-2 border-primary/20 animate-ping duration-1000" />
          
          {/* Rotating gradient rings */}
          <div className="absolute inset-1.5 rounded-full border-2 border-t-primary border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <div className="absolute inset-3 rounded-full border-2 border-b-secondary border-r-transparent border-t-transparent border-l-transparent animate-spin-reverse" />
          
          {/* Inner pulsing core with icon */}
          <div className="w-12 h-12 rounded-full bg-surface-container-lowest ring-1 ring-outline-variant/15 flex items-center justify-center shadow-lg">
            <Activity className="w-6 h-6 text-primary animate-pulse" />
          </div>
        </div>

        {/* Premium Typography & Micro-animations */}
        <h3 className="text-xl font-extrabold text-primary tracking-tight mb-2 uppercase">
          {title}
        </h3>
        
        <div className="flex items-center gap-2 text-xs font-bold text-secondary uppercase tracking-widest">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          <span>{displayMessage}</span>
        </div>

        {/* Progress bar simulation with shimmer */}
        <div className="w-48 h-1 bg-surface-container-high rounded-full mt-6 overflow-hidden relative border border-outline-variant/5">
          <div className="absolute top-0 left-0 h-full w-2/5 bg-gradient-to-r from-primary to-secondary rounded-full animate-shimmer" />
        </div>
      </div>
    </div>
  );
}
