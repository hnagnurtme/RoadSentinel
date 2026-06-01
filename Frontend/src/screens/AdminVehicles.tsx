import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Car, Plus, X, Search, ShieldAlert, AlertTriangle, ExternalLink, Clock, Users } from "lucide-react";
import { getVehicles, createVehicle } from "@/api/vehicles";
import { getUsers, getDrivingSessions } from "@/api/users";
import type { Vehicle } from "@/types/vehicle";
import { ImageUploader } from "@/components/ImageUploader";
import { listAlerts } from "@/api/alerts";
import type { Alert } from "@/types/alert";

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
        <div className="max-w-4xl mx-auto flex flex-col gap-8 relative animate-in fade-in duration-300">
            {/* Profile Header */}
            <div className="bg-surface-container rounded-2xl p-6 flex items-start gap-6 relative">
                <button
                    onClick={ onClose }
                    className="absolute top-6 right-6 p-2 rounded-lg bg-surface-container-high text-secondary hover:text-primary transition-colors"
                    title="Close Details"
                >
                    <X className="w-4 h-4" />
                </button>
                <div className="w-44 aspect-[16/10] rounded-xl bg-surface-container-highest overflow-hidden flex items-center justify-center border border-outline-variant/20 shadow-inner shrink-0">
                    { vehicle.vehicleImageUrl ? (
                        <img src={ vehicle.vehicleImageUrl } alt={ vehicle.plateNumber } className="w-full h-full object-cover" />
                    ) : (
                        <Car className="w-12 h-12 text-secondary opacity-30" />
                    ) }
                </div>
                <div className="flex-1 pr-12 flex flex-col justify-center h-28">
                    <span className="text-xs font-bold text-primary bg-primary/10 px-2.5 py-0.5 rounded uppercase tracking-wider font-mono self-start">
                        { vehicle.plateNumber }
                    </span>
                    <h2 className="text-2xl font-black text-on-surface mt-3">{ vehicle.manufacturer } { vehicle.model }</h2>
                    <p className="text-sm text-secondary mt-1">VIN: <span className="font-mono text-on-surface font-semibold">{ vehicle.vin || "N/A" }</span></p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Vehicle Specifications */}
                <div className="flex flex-col gap-4">
                    <h3 className="text-lg font-bold flex items-center gap-2 text-on-surface">
                        Vehicle Specifications
                    </h3>
                    <div className="bg-surface-container rounded-xl p-6 flex flex-col gap-4">
                        <div className="flex justify-between text-sm">
                            <span className="text-secondary font-medium">Production Year</span>
                            <span className="text-on-surface font-bold">{ vehicle.productionYear || "N/A" }</span>
                        </div>
                        <div className="flex justify-between border-t border-surface-container-high pt-4 text-sm">
                            <span className="text-secondary font-medium">Color</span>
                            <span className="text-on-surface font-bold">{ vehicle.color || "N/A" }</span>
                        </div>
                        <div className="flex justify-between border-t border-surface-container-high pt-4 text-sm">
                            <span className="text-secondary font-medium">Active Alert Count</span>
                            <span className={`font-bold ${alerts.length > 0 ? "text-error" : "text-emerald-500"}`}>
                                {loading ? "Loading..." : `${alerts.length} incidents`}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Driver Driving History */}
                <div className="flex flex-col gap-4">
                    <h3 className="text-lg font-bold flex items-center gap-2 text-on-surface">
                        <Clock className="w-5 h-5 text-primary" /> Driver Log & Driving Hours
                    </h3>
                    <div className="bg-surface-container rounded-xl overflow-hidden">
                        { loading ? (
                            <div className="p-4 text-center text-secondary text-sm">Loading history...</div>
                        ) : history.length === 0 ? (
                            <div className="p-4 text-center text-secondary text-sm">No driving log found for this vehicle.</div>
                        ) : (
                            <div className="flex flex-col divide-y divide-surface-container-high max-h-[400px] overflow-y-auto">
                                { history.map( (session, index) => {
                                    const isActive = session.status === "ACTIVE";
                                    return (
                                        <div key={ index } className={`p-4 flex flex-col gap-1.5 transition-colors ${isActive ? "bg-emerald-500/5" : ""}`}>
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm font-bold flex items-center gap-1.5">
                                                    <Users className="w-4 h-4 text-primary shrink-0" />
                                                    { session.driverName }
                                                </span>
                                                { isActive ? (
                                                    <span className="text-xs font-black text-emerald-600 bg-emerald-500/10 px-2.5 py-0.5 rounded animate-pulse">
                                                        Currently Driving
                                                    </span>
                                                ) : (
                                                    <span className="text-xs font-bold text-secondary bg-surface-container-high px-2 py-0.5 rounded">
                                                        Completed
                                                    </span>
                                                ) }
                                            </div>
                                            
                                            <div className="flex flex-col gap-0.5 text-xs text-secondary pl-5.5">
                                                <div className="flex justify-between">
                                                    <span>Started: { new Date( session.startedAt ).toLocaleString( 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } ) }</span>
                                                    <span className={`font-semibold ${isActive ? "text-emerald-600 font-bold" : "text-on-surface"}`}>
                                                        Hours: { session.duration }
                                                    </span>
                                                </div>
                                                { !isActive && session.endedAt && (
                                                    <span>Ended: { new Date( session.endedAt ).toLocaleString( 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } ) }</span>
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
    setNewImageUrl("");
    setFormError(null);
  };

  const filteredVehicles = vehicles.filter(v => 
    v.plateNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.manufacturer.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.model.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full bg-surface-container-lowest relative">
      <div className="flex items-center justify-between px-8 py-6 border-b border-surface-container-high bg-surface-container-lowest/80 backdrop-blur-xl sticky top-0 z-20 gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight text-primary">Fleet Vehicles</h1>
          <p className="text-sm text-secondary">Manage vehicles and monitor dynamic operational alerts.</p>
        </div>
        
        <div className="flex items-center gap-4 flex-1 max-w-md ml-auto">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-secondary" />
            <input
              type="text"
              placeholder="Search plate, manufacturer..."
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
            className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 transition-opacity shrink-0"
          >
            <Plus className="w-5 h-5" /> Add Vehicle
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Vehicle List */}
        <div className="w-1/3 border-r border-surface-container-high overflow-y-auto bg-surface-container-lowest/50 flex flex-col">
          <div className="flex-1 overflow-y-auto divide-y divide-surface-container-high">
            {loading ? (
              <div className="p-8 text-center text-secondary text-sm">Loading vehicles...</div>
            ) : filteredVehicles.length === 0 ? (
              <div className="p-8 text-center text-secondary text-sm">No vehicles found.</div>
            ) : (
              filteredVehicles.map(vehicle => (
                <button
                  key={vehicle.id}
                  onClick={() => setSelectedVehicle(vehicle)}
                  className={`flex items-start gap-4 p-4 text-left w-full transition-colors border-l-4 ${
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
              <p>Select a vehicle from the list to view details</p>
            </div>
          )}
        </div>
      </div>

      {isAddModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b border-surface-container-high shrink-0">
              <h2 className="text-xl font-bold">Add New Vehicle</h2>
              <button onClick={() => setIsAddModalOpen(false)} className="p-2 hover:bg-surface-container-low rounded-full">
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
                    label="Vehicle Image" 
                    currentUrl={newImageUrl} 
                    onUploadSuccess={setNewImageUrl} 
                  />
                </div>
                
                <div className="flex-1 flex flex-col gap-4">
                  <div className="grid grid-cols-1 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">Plate Number *</label>
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
                      <label className="text-sm font-bold text-secondary">Manufacturer *</label>
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
                      <label className="text-sm font-bold text-secondary">Model *</label>
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
                      <label className="text-sm font-bold text-secondary">Year</label>
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
                      <label className="text-sm font-bold text-secondary">Color</label>
                      <input
                        type="text"
                        value={newColor}
                        onChange={e => setNewColor(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="Silver"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-sm font-bold text-secondary">VIN</label>
                      <input
                        type="text"
                        value={newVin}
                        onChange={e => setNewVin(e.target.value)}
                        className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                        placeholder="JT..."
                      />
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-surface-container-high">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-lg font-bold text-secondary hover:bg-surface-container-high"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-primary text-on-primary px-6 py-2 rounded-lg font-bold hover:opacity-90"
                >
                  Create Vehicle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
