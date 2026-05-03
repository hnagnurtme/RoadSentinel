import { Outlet } from "react-router-dom";
import { DriverSidebar } from "@/components/DriverSidebar";

export function DriverLayout() {
  return (
    <div className="bg-background text-on-surface flex min-h-screen overflow-x-hidden font-sans">
      <DriverSidebar />
      <main className="flex-1 ml-64 flex flex-col gap-0 max-w-full">
        <Outlet />
      </main>
    </div>
  );
}