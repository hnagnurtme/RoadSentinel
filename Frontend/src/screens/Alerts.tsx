import { MapComponent } from "@/components/MapComponent";
import { AlertsTable } from "@/features/alerts/components/AlertsTable";
import { RealtimeAlertsPanel } from "@/features/alerts/components/RealtimeAlertsPanel";
import { useAlertsFeed } from "@/features/alerts/hooks/useAlertsFeed";
import { Alert } from "@/types/alert";

interface AlertsProps {
  onReviewAlert: (alert: Alert) => void;
}

export function Alerts({ onReviewAlert }: AlertsProps) {
  const { alerts, newAlertIds, isLoading, errorMessage, deleteAlert } = useAlertsFeed({ limit: 30 });

  return (
    <div className="p-8 space-y-8 max-w-[1600px] w-full mx-auto">
      <section className="grid grid-cols-1 lg:grid-cols-10 gap-6 h-[500px]">
        <div className="lg:col-span-7 h-full">
          <MapComponent alerts={alerts} onReviewAlert={onReviewAlert} />
        </div>

        <RealtimeAlertsPanel alerts={alerts} newAlertIds={newAlertIds} onViewIncident={onReviewAlert} />
      </section>

      <AlertsTable
        alerts={alerts}
        newAlertIds={newAlertIds}
        isLoading={isLoading}
        errorMessage={errorMessage}
        onReview={onReviewAlert}
        onDelete={deleteAlert}
      />
    </div>
  );
}
