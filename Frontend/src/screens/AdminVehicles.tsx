import React, { useState, useEffect } from "react";
import { Car, Plus, X, Search, ShieldAlert } from "lucide-react";
import { getVehicles, createVehicle } from "@/api/vehicles";
import type { Vehicle } from "@/types/vehicle";
import { ImageUploader } from "@/components/ImageUploader";

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
    <div className="p-10 max-w-[1600px] space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface-variant block mb-2">
            Admin Management
          </span>
          <h2 className="text-3xl font-black text-primary tracking-tight">Fleet Vehicles</h2>
        </div>
        <button
          onClick={() => {
            resetForm();
            setIsAddModalOpen(true);
          }}
          className="bg-primary text-on-primary px-6 py-3 rounded-lg font-bold hover:opacity-90 transition-opacity flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Add Vehicle
        </button>
      </div>

      <div className="flex items-center gap-4 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/30 shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-secondary" />
          <input
            type="text"
            placeholder="Search by plate, make, or model..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-surface-container rounded-lg pl-10 pr-4 py-2 focus:ring-2 focus:ring-primary outline-none"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-error-container text-on-error-container rounded-lg text-sm font-bold flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center p-20 text-secondary">
          Loading vehicles...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredVehicles.map(vehicle => (
            <div key={vehicle.id} className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm overflow-hidden flex flex-col group hover:shadow-md transition-shadow">
              <div className="aspect-[16/9] w-full bg-surface-container flex items-center justify-center overflow-hidden border-b border-outline-variant/20">
                {vehicle.vehicleImageUrl ? (
                  <img src={vehicle.vehicleImageUrl} alt={vehicle.plateNumber} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                ) : (
                  <Car className="w-12 h-12 text-secondary opacity-20" />
                )}
              </div>
              <div className="p-5 flex flex-col gap-4 flex-1">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xl font-black text-primary tracking-tight">{vehicle.plateNumber}</span>
                  </div>
                  <h3 className="text-sm font-semibold text-secondary">{vehicle.manufacturer} {vehicle.model}</h3>
                </div>
                
                <div className="grid grid-cols-2 gap-y-3 gap-x-2 text-xs mt-auto pt-4 border-t border-surface-container-high">
                  <div className="flex flex-col">
                    <span className="text-outline font-bold uppercase text-[9px] tracking-wider">Color</span>
                    <span className="text-on-surface-variant font-medium">{vehicle.color || "N/A"}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-outline font-bold uppercase text-[9px] tracking-wider">Year</span>
                    <span className="text-on-surface-variant font-medium">{vehicle.productionYear || "N/A"}</span>
                  </div>
                  <div className="flex flex-col col-span-2">
                    <span className="text-outline font-bold uppercase text-[9px] tracking-wider">VIN</span>
                    <span className="text-on-surface-variant font-medium font-mono">{vehicle.vin || "N/A"}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {filteredVehicles.length === 0 && (
            <div className="col-span-full py-20 flex flex-col items-center justify-center text-secondary border-2 border-dashed border-outline-variant/30 rounded-xl">
              <Car className="w-12 h-12 opacity-20 mb-4" />
              <p className="font-semibold text-lg">No vehicles found</p>
              <p className="text-sm opacity-70">Try adjusting your search or add a new vehicle.</p>
            </div>
          )}
        </div>
      )}

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
