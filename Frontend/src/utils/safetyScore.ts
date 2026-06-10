import { Alert, getAlertSeverity } from "@/types/alert";
import { Appeal } from "@/types/appeal";

export function calculateSafetyScore(driverId: string, alerts: Alert[], appeals: Appeal[], currentMonthOnly = false): number {
  let driverAlerts = alerts.filter(a => a.driverId === driverId);
  const driverAppeals = appeals.filter(ap => ap.driverId === driverId);
  
  if (currentMonthOnly) {
    const now = new Date();
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    driverAlerts = driverAlerts.filter(a => {
      if (!a.createdAt) return false;
      const alertDate = new Date(a.createdAt);
      return alertDate >= startOfMonth;
    });
  }
  
  // Map alertId to appeal status
  const appealStatusMap: Record<string, string> = {};
  driverAppeals.forEach(ap => {
    appealStatusMap[ap.alertId] = ap.status;
  });

  let score = 100;
  driverAlerts.forEach(alert => {
    const status = appealStatusMap[alert.id];
    // If the appeal is approved, ignore this alert (0 deduction)
    if (status === "APPROVED") {
      return;
    }
    
    // Otherwise, deduct based on severity
    const severity = getAlertSeverity(alert.alertType);
    if (severity === "critical") {
      score -= 10;
    } else if (severity === "moderate") {
      score -= 5;
    } else {
      score -= 2;
    }
  });

  return Math.max(0, score);
}

export function getSafetyScoreLabel(score: number, language: "en" | "vi"): { label: string; colorClass: string; textClass: string; bgClass: string } {
  if (score >= 80) {
    return {
      label: language === "en" ? "Safe" : "An toàn",
      colorClass: "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20",
      textClass: "text-emerald-600",
      bgClass: "bg-emerald-500"
    };
  }
  if (score >= 50) {
    return {
      label: language === "en" ? "Caution" : "Cảnh báo",
      colorClass: "bg-amber-500/10 text-amber-600 border border-amber-500/20",
      textClass: "text-amber-600",
      bgClass: "bg-amber-500"
    };
  }
  return {
    label: language === "en" ? "High Risk" : "Nguy hiểm",
    colorClass: "bg-rose-500/10 text-rose-600 border border-rose-500/20",
    textClass: "text-rose-600",
    bgClass: "bg-rose-500"
  };
}
