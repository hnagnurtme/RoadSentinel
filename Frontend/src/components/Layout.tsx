import { ReactNode } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AppView } from "@/App";

export interface LayoutProps {
  children: ReactNode;
  currentView: AppView;
  onNavigate: (view: AppView) => void;
  onOpenMonitor?: (deviceId: string) => void;
}

export function Layout({ children, currentView, onNavigate, onOpenMonitor }: LayoutProps) {
  return (
    <div className="bg-background text-on-surface flex min-h-screen overflow-x-hidden font-sans">
      <Sidebar currentView={currentView} onNavigate={onNavigate} onOpenMonitor={onOpenMonitor} />
      <main className="flex-1 ml-64 flex flex-col gap-0 max-w-full">
        <Header />
        {children}
      </main>
    </div>
  );
}
