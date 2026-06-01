import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Car, Plus, X, Search, ShieldAlert, AlertTriangle, ExternalLink, Clock, Users } from "lucide-react";
import { getVehicles, createVehicle } from "@/api/vehicles";
import { getUsers, getDrivingSessions } from "@/api/users";
import type { Vehicle } from "@/types/vehicle";
import { ImageUploader } from "@/components/ImageUploader";
import { listAlerts } from "@/api/alerts";
import type { Alert } from "@/types/alert";
import { useLanguage } from "@/i18n/LanguageContext";

function calculateDuration(startStr: string, endStr?: string | null): string {
    const start = new Date(startStr);
    const end = endStr ? new Date(endStr) : new Date();
    const diffMs = end.getTime() - start.getTime();
    if (diffMs < 0) return "0m";
    
    const diffMins = Math.floor(diffMs / 60000);
    const hrs = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    
    if (hrs > 0) {
        return `${hrs}h ${mins}m`;
    }
    return `${mins}m`;
}

interface DriverDrivingHistory {
    driverName: string;
    driverEmail: string;
    startedAt: string;
    endedAt: string | null;
    duration: string;
    status: string;
}

function VehicleDetails({ vehicle, onClose }: { vehicle: Vehicle; onClose: () => void }) {
    const { t } = useLanguage();
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [history, setHistory] = useState<DriverDrivingHistory[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let isCurrent = true;
        setLoading(true);

        const fetchHistory = async () => {
            try {
                // 1. Fetch alerts for this vehicle
                const vehicleAlerts = await listAlerts(100, undefined, vehicle.id);
                if (isCurrent) {
                    setAlerts(vehicleAlerts);
                }
                
                // 2. Identify unique drivers
                const driverIds = Array.from(new Set(
                    vehicleAlerts
                        .map(a => a.driverId)
                        .filter((id): id is string => !!id)
                ));

                if (driverIds.length === 0) {
                    if (isCurrent) {
                        setHistory([]);
                        setLoading(false);
                    }
                    return;
                }

                // Fetch details for all users to map names
                const allUsers = await getUsers();
                const userMap = new Map(allUsers.map(u => [u.id, u]));

                // 3. For each driver, fetch their sessions and correlate
                const correlatedSessions: DriverDrivingHistory[] = [];

                await Promise.all(driverIds.map(async (driverId) => {
                    const sessions = await getDrivingSessions(driverId);
                    const user = userMap.get(driverId);
                    const driverName = user?.name || user?.email || "Unknown Driver";
                    const driverEmail = user?.email || "";

                    // For each session, check if there are alerts for this vehicle during the session timeframe
                    sessions.forEach(session => {
                        const start = new Date(session.started_at).getTime();
                        const end = session.ended_at ? new Date(session.ended_at).getTime() : Date.now();

                        const hasOverlap = vehicleAlerts.some(alert => {
                            if (alert.driverId !== driverId) return false;
                            if (!alert.createdAt) return false;
                            const alertTime = new Date(alert.createdAt).getTime();
                            return alertTime >= start && alertTime <= end;
                        });

                        // If there is an alert during this session, map it to this vehicle!
                        if (hasOverlap) {
                            correlatedSessions.push({
                                driverName,
                                driverEmail,
                                startedAt: session.started_at,
                                endedAt: session.ended_at,
                                duration: calculateDuration(session.started_at, session.ended_at),
                                status: session.status
                            });
                        }
                    });
                }));

                // Sort by startedAt desc
                correlatedSessions.sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime());

                if (isCurrent) {
                    setHistory(correlatedSessions);
                }
            } catch (err) {
                console.error("Failed to compile vehicle driving history", err);
            } finally {
                if (isCurrent) {
                    setLoading(false);
                }
            }
        };

        fetchHistory();

        return () => {
            isCurrent = false;
        };
    }, [vehicle.id]);

    return (
        <div className="max-w-4xl mx-auto flex flex-col gap-4 relative animate-in fade-in duration-300">
            {/* Profile Header */}
            <div className="bg-surface-container rounded-2xl p-4 flex items-start gap-4 relative">
                <button
                    onClick={ onClose }
                    className="absolute top-4 right-4 p-2 rounded-lg bg-surface-container-high text-secondary hover:text-primary transition-colors"
                    title={t("common.close")}
                >
                    <X className="w-3.5 h-3.5" />
                </button>
                <div className="w-32 aspect-[16/10] rounded-xl bg-surface-container-highest overflow-hidden flex items-center justify-center border border-outline-variant/20 shadow-inner shrink-0">
                    { vehicle.vehicleImageUrl ? (
                        <img src={ vehicle.vehicleImageUrl } alt={ vehicle.plateNumber } className="w-full h-full object-cover" />
                    ) : (
                        <Car className="w-8 h-8 text-secondary opacity-30" />
                    ) }
                </div>
                <div className="flex-1 pr-12 flex flex-col justify-center h-20">
                    <span className="text-[10px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded uppercase tracking-wider font-mono self-start">
                        { vehicle.plateNumber }
                    </span>
                    <h2 className="text-lg font-black text-on-surface mt-1">{ vehicle.manufacturer } { vehicle.model }</h2>
                    <p className="text-xs text-secondary mt-0.5">VIN: <span className="font-mono text-on-surface font-semibold">{ vehicle.vin || "N/A" }</span></p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Vehicle Specifications */}
                <div className="flex flex-col gap-2.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5">
                        {t("vehicles.specs")}
                    </h3>
                    <div className="bg-surface-container rounded-xl p-4 flex flex-col gap-3">
                        <div className="flex justify-between text-xs">
                            <span className="text-secondary font-medium">{t("vehicles.productionYear")}</span>
                            <span className="text-on-surface font-bold">{ vehicle.productionYear || "N/A" }</span>
                        </div>
                        <div className="flex justify-between border-t border-surface-container-high pt-3 text-xs">
                            <span className="text-secondary font-medium">{t("vehicles.color")}</span>
                            <span className="text-on-surface font-bold">{ vehicle.color || "N/A" }</span>
                        </div>
                        <div className="flex justify-between border-t border-surface-container-high pt-3 text-xs">
                            <span className="text-secondary font-medium">Device ID</span>
                            <span className="text-on-surface font-bold font-mono text-[10px] select-all">{ vehicle.deviceId || "N/A" }</span>
                        </div>
                        <div className="flex justify-between border-t border-surface-container-high pt-3 text-xs">
                            <span className="text-secondary font-medium">{t("vehicles.activeAlerts")}</span>
                            <span className={`font-bold ${alerts.length > 0 ? "text-error" : "text-emerald-500"}`}>
                                {loading ? t("common.loading") : `${alerts.length} ${t("vehicles.incidents")}`}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Driver Driving History */}
                <div className="flex flex-col gap-2.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-secondary flex items-center gap-1.5">
                        <Clock className="w-4 h-4 text-primary" /> {t("vehicles.driverLog")}
                    </h3>
                    <div className="bg-surface-container rounded-xl overflow-hidden">
                        { loading ? (
                            <div className="p-4 text-center text-secondary text-xs">{t("common.loading")}</div>
                        ) : history.length === 0 ? (
                            <div className="p-4 text-center text-secondary text-xs">{t("vehicles.noLog")}</div>
                        ) : (
                            <div className="flex flex-col divide-y divide-surface-container-high max-h-[380px] overflow-y-auto">
                                { history.map( (session, index) => {
                                    const isActive = session.status === "ACTIVE";
                                    return (
                                        <div key={ index } className={`p-2.5 flex flex-col gap-1 transition-colors ${isActive ? "bg-emerald-500/5" : ""}`}>
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-bold flex items-center gap-1">
                                                    <Users className="w-3.5 h-3.5 text-primary shrink-0" />
                                                    { session.driverName }
                                                </span>
                                                { isActive ? (
                                                    <span className="text-[10px] font-black text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded animate-pulse">
                                                        {t("vehicles.currentlyDriving")}
                                                    </span>
                                                ) : (
                                                    <span className="text-[10px] font-bold text-secondary bg-surface-container-high px-1.5 py-0.5 rounded">
                                                        {t("vehicles.completed")}
                                                    </span>
                                                ) }
                                            </div>
                                            
                                            <div className="flex flex-col gap-0.5 text-[11px] text-secondary pl-4.5">
                                                <div className="flex justify-between">
                                                    <span>{t("vehicles.started")}: { new Date( session.startedAt ).toLocaleString( 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } ) }</span>
                                                    <span className={`font-semibold ${isActive ? "text-emerald-600 font-bold" : "text-on-surface"}`}>
                                                        {t("vehicles.hours")}: { session.duration }
                                                    </span>
                                                </div>
                                                { !isActive && session.endedAt && (
                                                    <span>{t("vehicles.ended")}: { new Date( session.endedAt ).toLocaleString( 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } ) }</span>
                                                )}
                                            </div>
                                        </div>
                                    );
                                } ) }
                            </div>
                        ) }
                    </div>
                </div>
            </div>
        </div>
    );
}

export function AdminVehicles() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newPlateNumber, setNewPlateNumber] = useState("");
  const [newManufacturer, setNewManufacturer] = useState("");
  const [newModel, setNewModel] = useState("");
  const [newColor, setNewColor] = useState("");
  const [newYear, setNewYear] = useState("");
  const [newVin, setNewVin] = useState("");
  const [newDeviceId, setNewDeviceId] = useState("");
  const [newImageUrl, setNewImageUrl] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      setLoading(true);
      const data = await getVehicles();
      setVehicles(data);
    } catch (err) {
      setError("Failed to load vehicles.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      const year = newYear ? parseInt(newYear, 10) : undefined;
      const created = await createVehicle({
        plate_number: newPlateNumber,
        manufacturer: newManufacturer,
        model: newModel,
        color: newColor || undefined,
        production_year: year,
        vin: newVin || undefined,
        device_id: newDeviceId || undefined,
        vehicle_image_url: newImageUrl || undefined,
      });
      setVehicles(prev => [created, ...prev]);
      setIsAddModalOpen(false);
      resetForm();
    } catch (err: any) {
      setFormError(err.message || "Failed to create vehicle.");
    }
  };

  const resetForm = () => {
    setNewPlateNumber("");
    setNewManufacturer("");
    setNewModel("");
    setNewColor("");
    setNewYear("");
    setNewVin("");
    setNewDeviceId("");
    setNewImageUrl("");
    setFormError(null);
  };

  const filteredVehicles = vehicles.filter(v => 
    v.plateNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.manufacturer.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.model.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const { t, language } = useLanguage();

  return (
    <div className="flex flex-col h-full bg-surface-container-lowest relative">
      <div className="flex items-center justify-between px-8 py-6 border-b border-surface-container-high bg-surface-container-lowest/80 backdrop-blur-xl sticky top-0 z-20 gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight text-primary">{t("vehicles.title")}</h1>
          <p className="text-sm text-secondary">{t("vehicles.subtitle")}</p>
        </div>
        
        <div className="flex items-center gap-4 flex-1 max-w-md ml-auto">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-secondary" />
            <input
              type="text"
              placeholder={t("vehicles.searchPlaceholder")}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-surface-container rounded-lg pl-9 pr-4 py-2 text-sm focus:ring-2 focus:ring-primary outline-none border border-outline-variant/10"
            />
          </div>
          <button
            onClick={() => {
              resetForm();
              setIsAddModalOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 transition-opacity shrink-0 cursor-pointer"
          >
            <Plus className="w-5 h-5" /> {t("vehicles.addVehicle")}
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Vehicle List */}
        <div className="w-1/3 border-r border-surface-container-high overflow-y-auto bg-surface-container-lowest/50 flex flex-col">
          <div className="flex-1 overflow-y-auto divide-y divide-surface-container-high">
            {loading ? (
              <div className="p-8 text-center text-secondary text-sm">{t("vehicles.loadingVehicles")}</div>
            ) : filteredVehicles.length === 0 ? (
              <div className="p-8 text-center text-secondary text-sm">{t("vehicles.noVehicles")}</div>
            ) : (
              filteredVehicles.map(vehicle => (
                <button
                  key={vehicle.id}
                  onClick={() => setSelectedVehicle(vehicle)}
                  className={`flex items-start gap-4 py-5 px-4 text-left w-full transition-colors border-l-4 cursor-pointer ${
                    selectedVehicle?.id === vehicle.id
                      ? "bg-primary/10 border-primary"
                      : "hover:bg-surface-container-low border-transparent"
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-on-surface truncate text-base">
                      {vehicle.manufacturer} {vehicle.model}
                    </h3>
                    <p className="text-sm text-secondary truncate mt-0.5 font-mono tracking-wide">
                      {vehicle.plateNumber}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {vehicle.color && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-surface-container-highest text-secondary">
                          {vehicle.color}
                        </span>
                      )}
                      {vehicle.productionYear && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-primary/10 text-primary">
                          {vehicle.productionYear}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Vehicle Details */}
        <div className="flex-1 overflow-y-auto p-8">
          {selectedVehicle ? (
            <VehicleDetails vehicle={selectedVehicle} onClose={() => setSelectedVehicle(null)} />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-secondary">
              <Car className="w-16 h-16 mb-4 opacity-20" />
              <p>{t("vehicles.selectVehicle")}</p>
            </div>
          )}
        </div>
      </div>

      {isAddModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b border-surface-container-high shrink-0">
              <h2 className="text-xl font-bold">{t("vehicles.addNewVehicle")}</h2>
              <button onClick={() => setIsAddModalOpen(false)} className="p-2 hover:bg-surface-container-low rounded-full cursor-pointer">
                <X className="w-5 h-5 text-secondary" />
              </button>
            </div>
            
            <form onSubmit={handleAddVehicle} className="p-6 flex flex-col gap-6 overflow-y-auto">
              {formError && (
                <div className="p-3 bg-error-container text-on-error-container rounded-lg text-sm font-bold flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4" />
                  {formError}
                </div>
              )}
              
              <div className="flex flex-col md:flex-row gap-6">
                <div className="w-full md:w-48 shrink-0 flex flex-col">
                  <ImageUploader 
                    label={t("vehicles.vehicleImage")} 
                    currentUrl={newImageUrl} 
                    onUploadSuccess={setNewImageUrl} 
                  />
                </div>
                
                <div className="flex-1 flex flex-col gap-4">
                  <div className="grid grid-cols-1 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">{t("vehicles.plateNumber")} *</label>
                      <input
                        type="text"
                        required
                        value={newPlateNumber}
                        onChange={e => setNewPlateNumber(e.target.value.toUpperCase())}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none font-mono"
                        placeholder="29A-123.45"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">{t("vehicles.manufacturer")} *</label>
                      <input
                        type="text"
                        required
                        value={newManufacturer}
                        onChange={e => setNewManufacturer(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="Toyota"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">{t("vehicles.model")} *</label>
                      <input
                        type="text"
                        required
                        value={newModel}
                        onChange={e => setNewModel(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="Innova"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">{t("vehicles.year")}</label>
                      <input
                        type="number"
                        value={newYear}
                        onChange={e => setNewYear(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="2023"
                        min="1900"
                        max={new Date().getFullYear() + 1}
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">{t("vehicles.color")}</label>
                      <input
                        type="text"
                        value={newColor}
                        onChange={e => setNewColor(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="Silver"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">{t("vehicles.vin")}</label>
                      <input
                        type="text"
                        value={newVin}
                        onChange={e => setNewVin(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="JT..."
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">Device ID</label>
                      <input
                        type="text"
                        value={newDeviceId}
                        onChange={e => setNewDeviceId(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="UUID (e.g. 3fa85f64-...)"
                      />
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-surface-container-high">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-lg font-bold text-secondary hover:bg-surface-container-high cursor-pointer"
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="submit"
                  className="bg-primary text-on-primary px-6 py-2 rounded-lg font-bold hover:opacity-90 cursor-pointer"
                >
                  {t("vehicles.addNewVehicle")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
