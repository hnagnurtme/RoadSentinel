/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Dashboard } from "@/screens/Dashboard";
import { IncidentReview } from "@/screens/IncidentReview";
import { Alerts } from "@/screens/Alerts";
import { Monitor } from "@/screens/Monitor";
import { Alert } from "@/types/alert";
import { getAlert } from "@/api/alerts";

export type AppView = "dashboard" | "incident" | "alerts" | "monitor";

function viewFromPath(pathname: string): AppView {
  if (pathname.startsWith("/monitor")) {
    return "monitor";
  }
  if (pathname.startsWith("/alerts")) {
    return "alerts";
  }
  return "dashboard";
}

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();

  const currentView = useMemo(() => viewFromPath(location.pathname), [location.pathname]);

  const navigateByView = (view: AppView, options?: { deviceId?: string }) => {
    if (view === "dashboard") {
      navigate("/dashboard");
      return;
    }
    if (view === "alerts") {
      navigate("/alerts");
      return;
    }
    if (view === "monitor") {
      if (options?.deviceId && options.deviceId.trim()) {
        navigate(`/monitor/${encodeURIComponent(options.deviceId)}`);
      } else {
        navigate("/monitor");
      }
      return;
    }

    // Incident always requires alert id, redirect to alerts when id is unknown.
    navigate("/alerts");
  };

  const openMonitor = (deviceId: string) => {
    navigateByView("monitor", { deviceId });
  };

  return (
    <Layout currentView={currentView} onNavigate={navigateByView} onOpenMonitor={openMonitor}>
      <Outlet />
    </Layout>
  );
}

function DashboardRoute() {
  const navigate = useNavigate();

  return (
    <Dashboard
      onNavigate={(view) => {
        if (view === "alerts") {
          navigate("/alerts");
          return;
        }
        if (view === "dashboard") {
          navigate("/dashboard");
          return;
        }
        navigate("/alerts");
      }}
    />
  );
}

function AlertsRoute() {
  const navigate = useNavigate();

  const openIncidentReview = (alert: Alert) => {
    navigate(`/alerts/${alert.id}`, { state: { alert } });
  };

  return <Alerts onReviewAlert={openIncidentReview} />;
}

function IncidentRoute() {
  const navigate = useNavigate();
  const location = useLocation();
  const { alertId } = useParams<{ alertId: string }>();

  const fromRouteState = (location.state as { alert?: Alert } | null)?.alert ?? null;
  const [alert, setAlert] = useState<Alert | null>(fromRouteState);

  useEffect(() => {
    const id = alertId?.trim();
    if (!id) {
      navigate("/alerts", { replace: true });
      return;
    }

    if (fromRouteState && fromRouteState.id === id) {
      setAlert(fromRouteState);
      return;
    }

    let cancelled = false;
    getAlert(id)
      .then((fetched) => {
        if (!cancelled) {
          setAlert(fetched);
        }
      })
      .catch(() => {
        if (!cancelled) {
          navigate("/alerts", { replace: true });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [alertId, fromRouteState, navigate]);

  return (
    <IncidentReview
      alert={alert}
      onNavigate={(view) => {
        if (view === "alerts") {
          navigate("/alerts");
        } else if (view === "dashboard") {
          navigate("/dashboard");
        }
      }}
    />
  );
}

function MonitorRoute() {
  const { deviceId } = useParams<{ deviceId: string }>();
  return <Monitor deviceId={deviceId ?? "esp32-cam"} />;
}

function LegacyIncidentRedirect() {
  const { alertId } = useParams<{ alertId: string }>();
  return <Navigate to={alertId ? `/alerts/${alertId}` : "/alerts"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardRoute />} />
        <Route path="/alerts" element={<AlertsRoute />} />
        <Route path="/alerts/:alertId" element={<IncidentRoute />} />
        <Route path="/incident/:alertId" element={<LegacyIncidentRedirect />} />
        <Route path="/monitor" element={<MonitorRoute />} />
        <Route path="/monitor/:deviceId" element={<MonitorRoute />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
