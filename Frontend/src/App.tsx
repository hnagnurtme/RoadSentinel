/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from "react";
import { Layout } from "@/components/Layout";
import { Dashboard } from "@/screens/Dashboard";
import { IncidentReview } from "@/screens/IncidentReview.tsx";
import { Alerts } from "@/screens/Alerts";
import { Alert } from "@/types/alert";

export default function App() {
  const [currentView, setCurrentView] = useState<"dashboard" | "incident" | "alerts">("dashboard");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const openIncidentReview = (alert: Alert) => {
    setSelectedAlert(alert);
    setCurrentView("incident");
  };

  return (
    <Layout currentView={currentView} onNavigate={setCurrentView}>
      {currentView === "dashboard" ? (
        <Dashboard onNavigate={setCurrentView} />
      ) : currentView === "incident" ? (
        <IncidentReview alert={selectedAlert} onNavigate={setCurrentView} />
      ) : (
        <Alerts onNavigate={setCurrentView} onReviewAlert={openIncidentReview} />
      )}
    </Layout>
  );
}

