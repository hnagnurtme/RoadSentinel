import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { IncidentReview } from "@/screens/IncidentReview";
import type { Alert } from "@/types/alert";
import { getAlert } from "@/api/alerts";

export function DriverIncidentRoute() {
  const navigate = useNavigate();
  const location = useLocation();
  const { alertId } = useParams<{ alertId: string }>();
  const fromState = (location.state as { alert?: Alert } | null)?.alert ?? null;
  const [alert, setAlert] = useState<Alert | null>(fromState);

  useEffect(() => {
    const id = alertId?.trim();
    if (!id) {
      navigate("/driver/violations", { replace: true });
      return;
    }
    if (fromState?.id === id) return;

    let cancelled = false;
    getAlert(id)
      .then((fetched) => {
        if (!cancelled) setAlert(fetched);
      })
      .catch(() => {
        if (!cancelled) navigate("/driver/violations", { replace: true });
      });
    return () => {
      cancelled = true;
    };
  }, [alertId, fromState, navigate]);

  return (
    <IncidentReview
      alert={alert}
      onNavigate={() => navigate("/driver/violations")}
      onBack={() => navigate("/driver/violations")}
      backLabel="Back to Violations"
    />
  );
}