import { getAlertSeverity } from "@/types/alert";

interface AlertSeverityBadgeProps {
  alertType: string;
}

const stylesBySeverity = {
  critical: "bg-error-container text-on-error-container",
  moderate: "bg-amber-100 text-amber-700",
  advisory: "bg-blue-100 text-blue-700",
};

export function AlertSeverityBadge({ alertType }: AlertSeverityBadgeProps) {
  const severity = getAlertSeverity(alertType);
  const label = severity.charAt(0).toUpperCase() + severity.slice(1);

  return (
    <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${stylesBySeverity[severity]}`}>
      {label}
    </span>
  );
}
