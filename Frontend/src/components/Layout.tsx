import { ReactNode } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";

interface LayoutProps {
  children: ReactNode;
  currentView: "dashboard" | "incident" | "alerts";
  onNavigate: (view: "dashboard" | "incident" | "alerts") => void;
}

export function Layout({ children, currentView, onNavigate }: LayoutProps) {
  return (
    <div className="bg-background text-on-surface flex min-h-screen overflow-x-hidden font-sans">
      <Sidebar currentView={currentView} onNavigate={onNavigate} />
      <main className="flex-1 ml-64 flex flex-col gap-0 max-w-full">
        <Header />
        {children}
      </main>
    </div>
  );
}
