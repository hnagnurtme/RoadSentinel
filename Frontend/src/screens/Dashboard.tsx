import { useEffect, useRef, useState, useCallback } from "react";
import { Calendar, ChevronDown, Download, Truck, Activity, AlertOctagon, Gauge } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { useLanguage } from "@/i18n/LanguageContext";
import { getUsers, getDrivingSessions, type User, type DrivingSession } from "@/api/users";
import { getVehicles } from "@/api/vehicles";
import { listAlerts } from "@/api/alerts";
import { listAppealsAdmin } from "@/api/appeals";
import type { Alert } from "@/types/alert";
import type { Appeal } from "@/types/appeal";
import { formatAlertTypeLabel, getAlertSeverity } from "@/types/alert";
import { calculateSafetyScore } from "@/utils/safetyScore";
import { ApiError } from "@/api/http";

interface DashboardProps {
  onNavigate: (view: string, alertId?: string, alert?: Alert) => void;
}

type DateRangeOption = "7days" | "30days" | "3months" | "all";

function useElementSize<T extends HTMLElement>() {
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [element, setElement] = useState<T | null>(null);

  const ref = useCallback((node: T | null) => {
    setElement(node);
  }, []);

  useEffect(() => {
    if (!element) {
      return;
    }

    const updateSize = () => {
      const nextWidth = Math.max(0, element.clientWidth);
      const nextHeight = Math.max(0, element.clientHeight);
      setSize({ width: nextWidth, height: nextHeight });
    };

    updateSize();

    const resizeObserver = new ResizeObserver(() => {
      updateSize();
    });
    resizeObserver.observe(element);

    return () => {
      resizeObserver.disconnect();
    };
  }, [element]);

  return { ref, width: size.width, height: size.height };
}

function calculatePercentChange(current: number, previous: number): string {
  if (previous === 0) {
    return current > 0 ? "+100%" : "0%";
  }
  const diff = ((current - previous) / previous) * 100;
  const sign = diff >= 0 ? "+" : "";
  return `${sign}${diff.toFixed(1)}%`;
}

function getPercentBadge(percentStr: string, isInverse = false) {
  const val = parseFloat(percentStr);
  if (isNaN(val) || val === 0) {
    return { text: percentStr, className: "text-secondary bg-surface-container-high/50 border border-outline-variant/10" };
  }
  const isPositive = val > 0;
  const isGood = isInverse ? !isPositive : isPositive;
  return {
    text: percentStr,
    className: isGood 
      ? "text-emerald-600 bg-emerald-500/10 border border-emerald-500/20" 
      : "text-error bg-error/10 border border-error/20"
  };
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const trendsChart = useElementSize<HTMLDivElement>();
  const riskChart = useElementSize<HTMLDivElement>();
  const { language, t } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRange, setSelectedRange] = useState<DateRangeOption>("30days");
  const [isDatePickerOpen, setIsDatePickerOpen] = useState(false);

  const [rawData, setRawData] = useState<{
    users: User[];
    vehicles: any[];
    alerts: Alert[];
    appeals: Appeal[];
    sessions: DrivingSession[];
  } | null>(null);

  const [metrics, setMetrics] = useState({
    activeAssets: 0,
    activeAssetsPct: "0%",
    totalDevices: 0,
    avgSafetyScore: 100,
    avgSafetyScorePct: "0%",
    criticalIncidents: 0,
    criticalIncidentsPct: "0%",
    totalDrivingHours: 0,
    totalDrivingHoursPct: "0%",
    dateRange: "",
    weeklyTrends: [] as Array<{ day: string; critical: number; moderate: number; advisory: number }>,
    riskDistribution: [] as Array<{ name: string; value: number; color: string }>,
    highRiskDrivers: [] as Array<{ name: string; id: string; score: number; avatar: string | null }>,
    recentIncidents: [] as Alert[]
  });

  // Load raw data when selectedRange changes
  useEffect(() => {
    let active = true;

    const loadAll = async () => {
      try {
        setLoading(true);
        setError(null);

        // First, fetch the latest alert to determine the baseline date of the dataset
        const latestAlerts = await listAlerts(1);
        let baselineDate = new Date();
        if (latestAlerts.length > 0 && latestAlerts[0].createdAt) {
          baselineDate = new Date(latestAlerts[0].createdAt);
        }

        // Calculate the start date of the previous cycle (to cover both cycles in one fetch)
        const endDate = new Date(baselineDate);
        let fetchStartDate = new Date(baselineDate);

        if (selectedRange === "7days") {
          fetchStartDate.setDate(fetchStartDate.getDate() - 14);
        } else if (selectedRange === "30days") {
          fetchStartDate.setDate(fetchStartDate.getDate() - 60);
        } else if (selectedRange === "3months") {
          fetchStartDate.setDate(fetchStartDate.getDate() - 180);
        } else {
          fetchStartDate = new Date(0); // All time
        }

        // Parallel fetch for alerts, users, vehicles, and appeals.
        // We set limit to 10000 to avoid any truncation and get all data within the range.
        const [users, vehicles, alertsData, appealsData] = await Promise.all([
          getUsers(),
          getVehicles(),
          listAlerts(
            10000, 
            undefined, 
            undefined, 
            selectedRange === "all" ? undefined : fetchStartDate.toISOString(),
            selectedRange === "all" ? undefined : endDate.toISOString()
          ),
          listAppealsAdmin()
        ]);

        if (!active) return;

        const driverUsers = users.filter(u => u.role === "driver");
        const sessionsPromises = driverUsers.map(u => getDrivingSessions(u.id));
        const sessionsResults = await Promise.all(sessionsPromises);
        const sessions = sessionsResults.flat();

        if (active) {
          setRawData({
            users: driverUsers,
            vehicles,
            alerts: alertsData,
            appeals: appealsData,
            sessions
          });
        }
      } catch (err) {
        console.error("Dashboard fetch error:", err);
        if (active) {
          if (err instanceof ApiError && err.status === 401) {
            setError("Your admin session expired. Please login again.");
          } else {
            setError("Failed to load dashboard data. Please try again.");
          }
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadAll();
    return () => {
      active = false;
    };
  }, [selectedRange]);

  // Filter and compute statistics dynamically when rawData or selectedRange changes
  useEffect(() => {
    if (!rawData) return;

    const { users, vehicles, alerts, appeals, sessions } = rawData;

    // 1. Establish baselineDate as latest alert date (or today if none)
    let baselineDate = new Date();
    if (alerts.length > 0 && alerts[0].createdAt) {
      baselineDate = new Date(alerts[0].createdAt);
    }

    // 2. Compute date boundaries for CURRENT cycle
    const endDate = new Date(baselineDate);
    let startDate = new Date(baselineDate);
    if (selectedRange === "7days") {
      startDate.setDate(startDate.getDate() - 7);
    } else if (selectedRange === "30days") {
      startDate.setDate(startDate.getDate() - 30);
    } else if (selectedRange === "3months") {
      startDate.setDate(startDate.getDate() - 90);
    } else {
      startDate = new Date(0); // All time
    }

    // 3. Compute date boundaries for PREVIOUS cycle of same length
    let prevEndDate = new Date(startDate);
    let prevStartDate = new Date(startDate);
    if (selectedRange === "7days") {
      prevStartDate.setDate(prevStartDate.getDate() - 7);
    } else if (selectedRange === "30days") {
      prevStartDate.setDate(prevStartDate.getDate() - 30);
    } else if (selectedRange === "3months") {
      prevStartDate.setDate(prevStartDate.getDate() - 90);
    } else {
      prevEndDate = new Date(0);
      prevStartDate = new Date(0);
    }

    // 4. Filter current & previous data arrays
    const currentAlerts = alerts.filter(a => {
      if (!a.createdAt) return false;
      const d = new Date(a.createdAt);
      return d >= startDate && d <= endDate;
    });

    const prevAlerts = alerts.filter(a => {
      if (!a.createdAt) return false;
      const d = new Date(a.createdAt);
      return d >= prevStartDate && d <= prevEndDate;
    });

    const currentSessions = sessions.filter(s => {
      const d = new Date(s.started_at);
      return d >= startDate && d <= endDate;
    });

    const prevSessions = sessions.filter(s => {
      const d = new Date(s.started_at);
      return d >= prevStartDate && d <= prevEndDate;
    });

    const currentAppeals = appeals.filter(ap => {
      if (!ap.createdAt) return false;
      const d = new Date(ap.createdAt);
      return d >= startDate && d <= endDate;
    });

    const prevAppeals = appeals.filter(ap => {
      if (!ap.createdAt) return false;
      const d = new Date(ap.createdAt);
      return d >= prevStartDate && d <= prevEndDate;
    });

    // 5. Calculate Metrics & Percentage Changes ("Cùng kỳ")
    // A. Active Assets (based on vehicles with associated devices)
    const vehiclesWithDevice = new Set(vehicles.filter(v => v.deviceId).map(v => v.id));
    const totalDevices = vehicles.filter(v => v.deviceId).length;

    const currentVehiclesSet = new Set(
      [...currentSessions.map(s => s.vehicle_id), ...currentAlerts.map(a => a.vehicleId)]
        .filter(Boolean)
        .filter(id => vehiclesWithDevice.has(id))
    );
    const prevVehiclesSet = new Set(
      [...prevSessions.map(s => s.vehicle_id), ...prevAlerts.map(a => a.vehicleId)]
        .filter(Boolean)
        .filter(id => vehiclesWithDevice.has(id))
    );
    const activeAssets = currentVehiclesSet.size;
    const activeAssetsPct = calculatePercentChange(activeAssets, prevVehiclesSet.size);

    // B. Safety Score average
    const currentScores = users.map(d => calculateSafetyScore(d.id, currentAlerts, currentAppeals));
    const currentAvg = currentScores.length > 0 ? Math.round(currentScores.reduce((a, b) => a + b, 0) / currentScores.length) : 100;
    const prevScores = users.map(d => calculateSafetyScore(d.id, prevAlerts, prevAppeals));
    const prevAvg = prevScores.length > 0 ? Math.round(prevScores.reduce((a, b) => a + b, 0) / prevScores.length) : 100;
    const avgSafetyScorePct = calculatePercentChange(currentAvg, prevAvg);

    // C. Critical Incidents
    const currentCritical = currentAlerts.filter(a => getAlertSeverity(a.alertType) === "critical").length;
    const prevCritical = prevAlerts.filter(a => getAlertSeverity(a.alertType) === "critical").length;
    const criticalIncidentsPct = calculatePercentChange(currentCritical, prevCritical);

    // D. Total Driving Hours
    const currentMs = currentSessions.reduce((sum, s) => {
      const start = new Date(s.started_at).getTime();
      const end = s.ended_at ? new Date(s.ended_at).getTime() : endDate.getTime();
      return sum + (end - start);
    }, 0);
    const currentHours = Math.round((currentMs / (1000 * 60 * 60)) * 10) / 10;

    const prevMs = prevSessions.reduce((sum, s) => {
      const start = new Date(s.started_at).getTime();
      const end = s.ended_at ? new Date(s.ended_at).getTime() : prevEndDate.getTime();
      return sum + (end - start);
    }, 0);
    const prevHours = Math.round((prevMs / (1000 * 60 * 60)) * 10) / 10;
    const totalDrivingHoursPct = calculatePercentChange(currentHours, prevHours);

    // E. Date range string
    let dateRange = "";
    if (selectedRange === "all" && alerts.length > 0) {
      const dates = alerts.map(a => a.createdAt ? new Date(a.createdAt).getTime() : 0).filter(t => t > 0);
      const minDate = new Date(Math.min(...dates));
      dateRange = `${minDate.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { month: "short", day: "numeric" })} - ${endDate.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { month: "short", day: "numeric", year: "numeric" })}`;
    } else {
      dateRange = `${startDate.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { month: "short", day: "numeric" })} - ${endDate.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { month: "short", day: "numeric", year: "numeric" })}`;
    }

    // F. Group trends based on range to ensure chart rendering
    const daysToRender = selectedRange === "7days" ? 7 : selectedRange === "30days" ? 30 : selectedRange === "3months" ? 90 : 30;
    const trendDates = Array.from({ length: daysToRender }).map((_, i) => {
      const d = new Date(endDate);
      d.setDate(d.getDate() - i);
      return d;
    }).reverse();

    const daysOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const weeklyTrends = trendDates.map(date => {
      const dateStr = date.toDateString();
      const dayAlerts = currentAlerts.filter(a => {
        if (!a.createdAt) return false;
        return new Date(a.createdAt).toDateString() === dateStr;
      });

      const critical = dayAlerts.filter(a => getAlertSeverity(a.alertType) === "critical").length;
      const moderate = dayAlerts.filter(a => getAlertSeverity(a.alertType) === "moderate").length;
      const advisory = dayAlerts.filter(a => getAlertSeverity(a.alertType) === "advisory").length;

      let label = "";
      if (daysToRender <= 7) {
        label = daysOfWeek[date.getDay()];
      } else {
        label = date.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { month: "short", day: "numeric" });
      }

      return {
        day: label,
        critical,
        moderate,
        advisory
      };
    });

    // G. Risk distribution
    const riskCounts: Record<string, number> = {};
    currentAlerts.forEach(a => {
      const typeLabel = formatAlertTypeLabel(a.alertType);
      riskCounts[typeLabel] = (riskCounts[typeLabel] || 0) + 1;
    });

    const colors = ['#0A2559', '#ba1a1a', '#515f74', '#c5c6d1', '#e0e3e5'];
    const riskDistribution = Object.entries(riskCounts)
      .map(([name, value], i) => ({
        name,
        value,
        color: colors[i % colors.length]
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 4);

    // H. High risk drivers list (re-score with current timeframe alerts)
    const driverScores = users.map(driver => {
      const score = calculateSafetyScore(driver.id, currentAlerts, currentAppeals);
      return {
        name: driver.name || driver.email,
        id: driver.id.split("-")[0].toUpperCase(),
        score,
        avatar: driver.avatar_image_url || null
      };
    });
    const sortedHighRisk = [...driverScores].sort((a, b) => a.score - b.score).slice(0, 4);

    // I. Recent incidents
    const recentIncidents = currentAlerts.slice(0, 5);

    setMetrics({
      activeAssets,
      activeAssetsPct,
      totalDevices,
      avgSafetyScore: currentAvg,
      avgSafetyScorePct,
      criticalIncidents: currentCritical,
      criticalIncidentsPct,
      totalDrivingHours: currentHours,
      totalDrivingHoursPct,
      dateRange,
      weeklyTrends,
      riskDistribution,
      highRiskDrivers: sortedHighRisk,
      recentIncidents
    });

  }, [rawData, selectedRange, language]);

  if (error) {
    return (
      <div className="p-10 max-w-[1600px]">
        <div className="text-sm font-semibold bg-error-container text-on-error-container px-4 py-3 rounded-xl border border-error/20">
          {error}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-[75vh] w-full flex flex-col items-center justify-center p-8 relative overflow-hidden">
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
            RoadSentinel
          </h3>
          
          <div className="flex items-center gap-2 text-xs font-bold text-secondary uppercase tracking-widest">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            <span>{language === "en" ? "Retrieving Fleet Analytics" : "Đang tải dữ liệu đội xe"}</span>
          </div>

          {/* Progress bar simulation with shimmer */}
          <div className="w-48 h-1 bg-surface-container-high rounded-full mt-6 overflow-hidden relative border border-outline-variant/5">
            <div className="absolute top-0 left-0 h-full w-2/5 bg-gradient-to-r from-primary to-secondary rounded-full animate-shimmer" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-10 flex flex-col gap-8 max-w-[1600px]">
      {/* Metrics Grid Header */}
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-primary">{t("dashboard.title")}</h2>
          <p className="text-secondary font-medium text-sm mt-1">{t("dashboard.subtitle")}</p>
        </div>
        <div className="flex gap-3">
          <div className="relative">
            <button 
              onClick={() => setIsDatePickerOpen(!isDatePickerOpen)}
              className="flex items-center gap-2 bg-surface-container-lowest ring-1 ring-outline-variant/15 shadow-sm px-4 py-2.5 rounded-lg font-bold text-xs hover:bg-surface-container-low transition-colors text-on-surface-variant cursor-pointer"
            >
              <Calendar className="w-4 h-4" />
              <span>{metrics.dateRange}</span>
              <ChevronDown className="w-4 h-4 text-outline" />
            </button>

            {isDatePickerOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/20 shadow-xl z-30 py-2 divide-y divide-surface-container-high animate-in fade-in slide-in-from-top-2 duration-150 border border-outline-variant/10">
                <div className="py-1">
                  {[
                    { key: "7days", label: t("dashboard.last7Days") },
                    { key: "30days", label: t("dashboard.last30Days") },
                    { key: "3months", label: t("dashboard.last3Months") },
                    { key: "all", label: t("dashboard.allTime") }
                  ].map(opt => (
                    <button
                      key={opt.key}
                      onClick={() => {
                        setSelectedRange(opt.key as any);
                        setIsDatePickerOpen(false);
                      }}
                      className={`flex items-center justify-between w-full px-4 py-2.5 text-xs font-bold text-left transition-colors cursor-pointer ${
                        selectedRange === opt.key 
                          ? "bg-primary/10 text-primary border-l-4 border-primary" 
                          : "text-secondary hover:bg-surface-container-low border-l-4 border-transparent"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button className="flex items-center gap-2 bg-primary text-on-primary px-4 py-2.5 rounded-lg font-bold text-xs hover:opacity-90 shadow-md transition-opacity cursor-pointer">
            <Download className="w-4 h-4" />
            <span>{language === "en" ? "Export Report" : "Xuất báo cáo"}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 - Active Assets */}
        {(() => {
          const badge = getPercentBadge(metrics.activeAssetsPct);
          return (
            <div 
              onClick={() => onNavigate("vehicles")}
              className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm hover:shadow-md hover:bg-surface-container-low transition-all duration-200 flex flex-col justify-between cursor-pointer group"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-primary-container/20 rounded-lg text-primary group-hover:scale-110 transition-transform">
                  <Truck className="w-5 h-5" />
                </div>
                {selectedRange !== "all" && (
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${badge.className}`}>{badge.text}</span>
                )}
              </div>
              <div>
                <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">
                  {language === "en" ? "Active Assets" : "Thiết bị hoạt động"}
                </p>
                <h3 className="text-3xl font-black text-primary tracking-tight">
                  {metrics.activeAssets}
                  <span className="text-sm text-outline font-medium"> / {metrics.totalDevices}</span>
                </h3>
              </div>
            </div>
          );
        })()}

        {/* Metric 2 - Average Safety Score */}
        {(() => {
          const badge = getPercentBadge(metrics.avgSafetyScorePct);
          return (
            <div 
              onClick={() => onNavigate("drivers")}
              className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm hover:shadow-md hover:bg-surface-container-low transition-all duration-200 flex flex-col justify-between cursor-pointer group"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-tertiary-container/20 rounded-lg text-tertiary group-hover:scale-110 transition-transform">
                  <Activity className="w-5 h-5" />
                </div>
                {selectedRange !== "all" && (
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${badge.className}`}>{badge.text}</span>
                )}
              </div>
              <div>
                <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">
                  {t("drivers.safetyScore")}
                </p>
                <h3 className="text-3xl font-black text-primary tracking-tight">
                  {metrics.avgSafetyScore}
                  <span className="text-sm text-outline font-medium">/100</span>
                </h3>
              </div>
            </div>
          );
        })()}

        {/* Metric 3 - Critical Incidents */}
        {(() => {
          const badge = getPercentBadge(metrics.criticalIncidentsPct, true); // True because increase in critical incidents is BAD
          return (
            <div 
              onClick={() => onNavigate("alerts")}
              className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm hover:shadow-md hover:bg-surface-container-low transition-all duration-200 flex flex-col justify-between cursor-pointer group"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-error-container text-error rounded-lg group-hover:scale-110 transition-transform">
                  <AlertOctagon className="w-5 h-5" />
                </div>
                {selectedRange !== "all" && (
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${badge.className}`}>{badge.text}</span>
                )}
              </div>
              <div>
                <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">
                  {language === "en" ? "Critical Incidents" : "Sự cố nghiêm trọng"}
                </p>
                <h3 className="text-3xl font-black text-primary tracking-tight">{metrics.criticalIncidents}</h3>
              </div>
            </div>
          );
        })()}

        {/* Metric 4 - Total Driving Hours */}
        {(() => {
          const badge = getPercentBadge(metrics.totalDrivingHoursPct);
          return (
            <div 
              onClick={() => onNavigate("drivers")}
              className="bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm hover:shadow-md hover:bg-surface-container-low transition-all duration-200 flex flex-col justify-between cursor-pointer group"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-secondary-container/50 text-secondary rounded-lg group-hover:scale-110 transition-transform">
                  <Gauge className="w-5 h-5" />
                </div>
                {selectedRange !== "all" && (
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${badge.className}`}>{badge.text}</span>
                )}
              </div>
              <div>
                <p className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">
                  {t("dashboard.totalMovingHours")}
                </p>
                <h3 className="text-3xl font-black text-primary tracking-tight">
                  {metrics.totalDrivingHours}
                  <span className="text-sm text-outline font-medium"> h</span>
                </h3>
              </div>
            </div>
          );
        })()}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Violation Trends */}
        <div className="lg:col-span-8 min-w-0 bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-lg font-bold text-primary">
                {language === "en" ? "Violation Trends" : "Xu hướng vi phạm"}
              </h3>
              <p className="text-xs text-secondary">
                {selectedRange === "7days" 
                  ? (language === "en" ? "Daily incident frequency across the last 7 days" : "Tần suất sự cố hàng ngày trong 7 ngày qua")
                  : selectedRange === "30days"
                  ? (language === "en" ? "Daily incident frequency across the last 30 days" : "Tần suất sự cố hàng ngày trong 30 ngày qua")
                  : selectedRange === "3months"
                  ? (language === "en" ? "Daily incident frequency across the last 3 months" : "Tần suất sự cố hàng ngày trong 3 tháng qua")
                  : (language === "en" ? "Daily incident frequency across the total period" : "Tần suất sự cố hàng ngày trong toàn bộ thời gian")}
              </p>
            </div>
          </div>
          <div ref={trendsChart.ref} className="h-72 w-full min-w-0 flex flex-col pt-4">
            {trendsChart.width > 0 && trendsChart.height > 0 && (
              <BarChart width={trendsChart.width} height={trendsChart.height} data={metrics.weeklyTrends} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e0e3e5" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#757780', fontWeight: 700 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#757780', fontWeight: 700 }} />
                <Tooltip 
                  cursor={{ fill: '#f2f4f6' }}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e0e3e5', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  labelStyle={{ fontWeight: 'bold', color: '#191c1e', marginBottom: '4px' }}
                />
                <Bar dataKey="advisory" stackId="a" fill="#515f74" radius={[0, 0, 4, 4]} />
                <Bar dataKey="moderate" stackId="a" fill="#0A2559" />
                <Bar dataKey="critical" stackId="a" fill="#ba1a1a" radius={[4, 4, 0, 0]} />
              </BarChart>
            )}
          </div>
          <div className="flex items-center gap-6 pt-4 border-t border-surface-container-high mt-4">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-error"></span>
              <span className="text-[10px] font-bold uppercase tracking-wide text-secondary">
                {language === "en" ? "Critical" : "Nghiêm trọng"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
              <span className="text-[10px] font-bold uppercase tracking-wide text-secondary">
                {language === "en" ? "Moderate" : "Trung bình"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-secondary"></span>
              <span className="text-[10px] font-bold uppercase tracking-wide text-secondary">
                {language === "en" ? "Advisory" : "Nhắc nhở"}
              </span>
            </div>
          </div>
        </div>

        {/* Risk Composition */}
        <div className="lg:col-span-4 min-w-0 bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm flex flex-col">
          <div className="mb-6">
            <h3 className="text-lg font-bold text-primary">{t("dashboard.incidentDistribution")}</h3>
            <p className="text-xs text-secondary">
              {language === "en" ? "Breakdown of primary behavioral risks" : "Phân tích các rủi ro hành vi chính"}
            </p>
          </div>
          <div className="flex-1 flex flex-col justify-center">
            {metrics.riskDistribution.length === 0 ? (
              <div className="text-center text-xs text-secondary py-10">
                {t("common.noData")}
              </div>
            ) : (
              <>
                <div ref={riskChart.ref} className="relative w-full min-w-0 h-48 mb-4">
                  {riskChart.width > 0 && riskChart.height > 0 && (
                    <PieChart width={riskChart.width} height={riskChart.height}>
                      <Pie
                        data={metrics.riskDistribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={2}
                        dataKey="value"
                        stroke="none"
                      >
                        {metrics.riskDistribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ borderRadius: '8px', border: '1px solid #e0e3e5', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        itemStyle={{ fontWeight: 'bold', color: '#191c1e' }}
                      />
                    </PieChart>
                  )}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-2xl font-black text-primary leading-none">{metrics.avgSafetyScore}</span>
                    <span className="text-[9px] font-bold text-outline uppercase tracking-tighter">
                      {language === "en" ? "Avg Score" : "Điểm số TB"}
                    </span>
                  </div>
                </div>
                <div className="space-y-2 max-h-[140px] overflow-y-auto pr-1">
                  {metrics.riskDistribution.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs bg-surface-container-low/50 p-2 rounded-lg ring-1 ring-outline-variant/15">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                        <span className="font-medium text-on-surface-variant truncate max-w-[150px]">{item.name}</span>
                      </div>
                      <span className="font-bold text-primary">{item.value}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* High-Risk Drivers & Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* High-Risk Drivers */}
        <div className="lg:col-span-4 bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-surface-container-high flex justify-between items-center bg-surface-container-low/30">
            <h3 className="text-sm font-bold text-primary uppercase tracking-wider">
              {language === "en" ? "High-Risk Drivers" : "Tài xế rủi ro cao"}
            </h3>
            <span className="text-[10px] font-bold text-error bg-error-container px-2 py-0.5 rounded uppercase">
              {language === "en" ? "Action Req" : "Cần xử lý"}
            </span>
          </div>
          <div className="divide-y divide-surface-container-high flex-1 overflow-y-auto max-h-[350px]">
            {metrics.highRiskDrivers.length === 0 ? (
              <div className="p-8 text-center text-xs text-secondary">
                {t("drivers.noDrivers")}
              </div>
            ) : (
              metrics.highRiskDrivers.map((driver, i) => (
                <div key={i} className="p-4 hover:bg-surface-container-low transition-colors flex items-center justify-between cursor-pointer" onClick={() => onNavigate("drivers")}>
                  <div className="flex items-center gap-3">
                    {driver.avatar ? (
                      <img src={driver.avatar} alt={driver.name} className="w-10 h-10 rounded-full object-cover ring-2 ring-surface-container-high" referrerPolicy="no-referrer" />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                        {driver.name.slice(0, 2).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-bold text-primary truncate max-w-[140px]">{driver.name}</p>
                      <p className="text-[10px] font-medium text-secondary uppercase tracking-wider">ID: {driver.id}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-black ${
                      driver.score >= 80 ? "text-emerald-600" : driver.score >= 60 ? "text-amber-600" : "text-error"
                    }`}>{driver.score}</p>
                    <p className="text-[9px] font-bold text-outline uppercase tracking-widest">
                      {language === "en" ? "Score" : "Điểm"}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="p-4 border-t border-surface-container-high bg-surface-container-low/30">
            <button className="w-full py-2 text-xs font-bold text-primary hover:bg-surface-container-low rounded transition-colors cursor-pointer" onClick={() => onNavigate("drivers")}>
              {language === "en" ? "View All Drivers" : "Xem tất cả tài xế"}
            </button>
          </div>
        </div>

        {/* Live Incident Feed */}
        <div className="lg:col-span-8 bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-surface-container-high flex justify-between items-center bg-surface-container-low/30">
            <h3 className="text-sm font-bold text-primary uppercase tracking-wider">{t("dashboard.recentIncidents")}</h3>
            <span className="text-[10px] font-bold text-outline uppercase">
              {language === "en" ? "Live Feed" : "Cập nhật trực tiếp"}
            </span>
          </div>
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-surface-container-low border-b border-surface-container-high">
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">{t("appeals.timestamp")}</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">{language === "en" ? "Asset ID" : "Mã phương tiện"}</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">{t("dashboard.severity")}</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">{t("appeals.incidentType")}</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary">{language === "en" ? "Geo-Location" : "Vị trí"}</th>
                  <th className="px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-secondary text-center">{t("appeals.actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container-high">
                {metrics.recentIncidents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-10 text-center text-xs text-secondary">
                      {t("dashboard.noRecentIncidents")}
                    </td>
                  </tr>
                ) : (
                  metrics.recentIncidents.map((a) => {
                    const plateNumber = a.vehicle?.plateNumber ?? a.vehicleId ?? "Unknown";
                    const severity = getAlertSeverity(a.alertType);
                    const severityBadgeClass = severity === "critical"
                      ? "bg-error-container text-on-error-container"
                      : severity === "moderate"
                      ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                      : "bg-blue-500/10 text-blue-600 border border-blue-500/20";

                    return (
                      <tr 
                        key={a.id} 
                        className="hover:bg-surface-container-low transition-colors cursor-pointer" 
                        onClick={() => onNavigate("alerts", a.id, a)}
                      >
                        <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">
                          {a.createdAt ? new Date(a.createdAt).toLocaleString(language === "vi" ? "vi-VN" : "en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "N/A"}
                        </td>
                        <td className="px-6 py-4 text-xs font-bold text-primary">{plateNumber}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${severityBadgeClass}`}>
                            {severity === "critical" ? (language === "en" ? "Critical" : "Nghiêm trọng") : severity === "moderate" ? (language === "en" ? "Moderate" : "Trung bình") : (language === "en" ? "Advisory" : "Nhắc nhở")}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs font-medium text-on-surface-variant">
                          {formatAlertTypeLabel(a.alertType)}
                        </td>
                        <td className="px-6 py-4 text-xs text-secondary">
                          {a.latitude != null && a.longitude != null ? `${a.latitude.toFixed(4)}, ${a.longitude.toFixed(4)}` : "Unknown"}
                        </td>
                        <td className="px-6 py-4 font-bold text-xs" onClick={(e) => e.stopPropagation()}>
                          <div className="flex justify-center gap-2">
                            <button 
                              onClick={() => {
                                onNavigate("alerts", a.id, a);
                              }}
                              className="bg-primary text-on-primary text-[9px] font-bold uppercase px-3 py-1.5 rounded hover:opacity-90 shadow-sm transition-opacity cursor-pointer animate-none"
                            >
                              {t("dashboard.review")}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
