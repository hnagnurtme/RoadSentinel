import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Fingerprint, Clock, AlertTriangle, Edit2, X, Check, Plus, ExternalLink } from "lucide-react";
import { getUsers, updateFingerprint, getDrivingSessions, createUser, User, DrivingSession } from "@/api/users";
import { listAlerts } from "@/api/alerts";
import { Alert } from "@/types/alert";

export function AdminDrivers() {
  const [drivers, setDrivers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDriver, setSelectedDriver] = useState<User | null>(null);

  // Add driver modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newDriverEmail, setNewDriverEmail] = useState("");
  const [newDriverPassword, setNewDriverPassword] = useState("");
  const [newDriverName, setNewDriverName] = useState("");
  const [newDriverAvatar, setNewDriverAvatar] = useState("");
  const [newDriverBirthday, setNewDriverBirthday] = useState("");
  const [newDriverGender, setNewDriverGender] = useState("");
  const [newDriverCity, setNewDriverCity] = useState("");
  const [newDriverCountry, setNewDriverCountry] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    fetchDrivers();
  }, []);

  const fetchDrivers = async () => {
    setLoading(true);
    try {
      const allUsers = await getUsers();
      const driverUsers = allUsers.filter(u => u.role === "driver");
      setDrivers(driverUsers);
      
      setSelectedDriver(prev => {
        if (!prev) return null;
        return driverUsers.find(d => d.id === prev.id) || prev;
      });
    } catch (err) {
      console.error("Failed to fetch drivers", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddDriver = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDriverEmail) return;
    setIsAdding(true);
    try {
      await createUser({ 
        email: newDriverEmail, 
        password: newDriverPassword || undefined,
        name: newDriverName || undefined,
        avatar_image_url: newDriverAvatar || undefined,
        birthday: newDriverBirthday || undefined,
        gender: newDriverGender || undefined,
        address__city: newDriverCity || undefined,
        address__country: newDriverCountry || undefined
      });
      setIsAddModalOpen(false);
      setNewDriverEmail("");
      setNewDriverPassword("");
      setNewDriverName("");
      setNewDriverAvatar("");
      setNewDriverBirthday("");
      setNewDriverGender("");
      setNewDriverCity("");
      setNewDriverCountry("");
      fetchDrivers();
    } catch (err) {
      console.error("Failed to add driver", err);
      alert("Failed to add driver. Please check inputs.");
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-container-lowest relative">
      <div className="flex items-center justify-between px-8 py-6 border-b border-surface-container-high bg-surface-container-lowest/80 backdrop-blur-xl sticky top-0 z-20">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight text-primary">Driver Management</h1>
          <p className="text-sm text-secondary">Manage driver profiles, fingerprints, and view history.</p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary font-bold rounded-lg hover:opacity-90 transition-opacity"
        >
          <Plus className="w-5 h-5" /> Add Driver
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Driver List */}
        <div className="w-1/3 border-r border-surface-container-high overflow-y-auto bg-surface-container-lowest/50">
          {loading ? (
            <div className="p-8 text-center text-secondary">Loading drivers...</div>
          ) : drivers.length === 0 ? (
            <div className="p-8 text-center text-secondary">No drivers found.</div>
          ) : (
            <div className="flex flex-col divide-y divide-surface-container-high">
              {drivers.map(driver => (
                <button
                  key={driver.id}
                  onClick={() => setSelectedDriver(driver)}
                  className={`flex items-start gap-4 p-4 text-left transition-colors ${
                    selectedDriver?.id === driver.id 
                      ? "bg-primary/10 border-l-4 border-primary" 
                      : "hover:bg-surface-container-low border-l-4 border-transparent"
                  }`}
                >
                  <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center shrink-0 overflow-hidden">
                    {driver.avatar_image_url ? (
                      <img src={driver.avatar_image_url} alt={driver.name || "Avatar"} className="w-full h-full object-cover" />
                    ) : (
                      <Users className="w-5 h-5 text-secondary" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-on-surface truncate">{driver.name || driver.email}</h3>
                    <p className="text-sm text-secondary truncate">{driver.email}</p>
                    {driver.fingerprint_id ? (
                      <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-600">
                        <Fingerprint className="w-3 h-3" /> Enrolled
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded text-xs font-medium bg-error/10 text-error">
                        <Fingerprint className="w-3 h-3" /> Not Enrolled
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Driver Details */}
        <div className="flex-1 overflow-y-auto p-8">
          {selectedDriver ? (
            <DriverDetails driver={selectedDriver} onUpdate={fetchDrivers} />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-secondary">
              <Users className="w-16 h-16 mb-4 opacity-20" />
              <p>Select a driver from the list to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Add Driver Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b border-surface-container-high shrink-0">
              <h2 className="text-xl font-bold">Add New Driver</h2>
              <button onClick={() => setIsAddModalOpen(false)} className="p-2 hover:bg-surface-container-low rounded-full">
                <X className="w-5 h-5 text-secondary" />
              </button>
            </div>
            <form onSubmit={handleAddDriver} className="p-6 flex flex-col gap-4 overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={newDriverEmail}
                    onChange={e => setNewDriverEmail(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="driver@example.com"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Password *</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={newDriverPassword}
                    onChange={e => setNewDriverPassword(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="Min 8 characters"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Full Name</label>
                  <input
                    type="text"
                    value={newDriverName}
                    onChange={e => setNewDriverName(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="John Doe"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Avatar URL</label>
                  <input
                    type="url"
                    value={newDriverAvatar}
                    onChange={e => setNewDriverAvatar(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="https://example.com/avatar.jpg"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Date of Birth</label>
                  <input
                    type="date"
                    value={newDriverBirthday}
                    onChange={e => setNewDriverBirthday(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Gender</label>
                  <select
                    value={newDriverGender}
                    onChange={e => setNewDriverGender(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                  >
                    <option value="">Select Gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">City</label>
                  <input
                    type="text"
                    value={newDriverCity}
                    onChange={e => setNewDriverCity(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="Da Nang"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Country</label>
                  <input
                    type="text"
                    value={newDriverCountry}
                    onChange={e => setNewDriverCountry(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="Vietnam"
                  />
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
                  disabled={isAdding || !newDriverEmail}
                  className="px-4 py-2 rounded-lg font-bold bg-primary text-on-primary hover:opacity-90 disabled:opacity-50"
                >
                  {isAdding ? "Adding..." : "Add Driver"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function DriverDetails({ driver, onUpdate }: { driver: User, onUpdate: () => void }) {
  const [sessions, setSessions] = useState<DrivingSession[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const navigate = useNavigate();
  
  const [isEditingFingerprint, setIsEditingFingerprint] = useState(false);
  const [newFingerprint, setNewFingerprint] = useState(driver.fingerprint_id || "");
  const [savingFingerprint, setSavingFingerprint] = useState(false);

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editAvatar, setEditAvatar] = useState("");
  const [editBirthday, setEditBirthday] = useState("");
  const [editGender, setEditGender] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editCountry, setEditCountry] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  useEffect(() => {
    setNewFingerprint(driver.fingerprint_id || "");
    setIsEditingFingerprint(false);
    
    setEditName(driver.name || "");
    setEditAvatar(driver.avatar_image_url || "");
    setEditBirthday(driver.birthday || "");
    setEditGender(driver.gender || "");
    setEditCity(driver.address__city || "");
    setEditCountry(driver.address__country || "");
    
    fetchHistory();
  }, [driver]);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const [sessionsData, alertsData] = await Promise.all([
        getDrivingSessions(driver.id),
        listAlerts(50, driver.id)
      ]);
      setSessions(sessionsData);
      setAlerts(alertsData);
    } catch (err) {
      console.error("Failed to fetch driver history", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleSaveFingerprint = async () => {
    setSavingFingerprint(true);
    try {
      await updateFingerprint(driver.id, newFingerprint);
      onUpdate();
      setIsEditingFingerprint(false);
    } catch (err) {
      console.error("Failed to update fingerprint", err);
      alert("Failed to update fingerprint ID.");
    } finally {
      setSavingFingerprint(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    try {
      const { updateUser } = await import("@/api/users");
      await updateUser(driver.id, {
        name: editName || null,
        avatar_image_url: editAvatar || null,
        birthday: editBirthday || null,
        gender: editGender || null,
        address__city: editCity || null,
        address__country: editCountry || null,
      });
      setIsEditModalOpen(false);
      onUpdate();
    } catch (err) {
      console.error("Failed to update profile", err);
      alert("Failed to update profile.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-8 relative">
      {/* Profile Header */}
      <div className="bg-surface-container rounded-2xl p-6 flex items-start gap-6 relative">
        <button 
          onClick={() => setIsEditModalOpen(true)}
          className="absolute top-6 right-6 p-2 rounded-lg bg-surface-container-high text-secondary hover:text-primary transition-colors"
          title="Edit Profile"
        >
          <Edit2 className="w-4 h-4" />
        </button>
        <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center shrink-0 overflow-hidden">
          {driver.avatar_image_url ? (
            <img src={driver.avatar_image_url} alt={driver.name || "Avatar"} className="w-full h-full object-cover" />
          ) : (
            <Users className="w-10 h-10 text-primary" />
          )}
        </div>
        <div className="flex-1 pr-12">
          <h2 className="text-2xl font-bold text-on-surface">{driver.name || "Unknown Name"}</h2>
          <p className="text-secondary mb-4">{driver.email}</p>
          
          <div className="flex flex-col gap-2">
            <h4 className="text-sm font-bold text-secondary uppercase tracking-wider">Fingerprint ID</h4>
            {isEditingFingerprint ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newFingerprint}
                  onChange={(e) => setNewFingerprint(e.target.value)}
                  className="bg-surface-container-highest border-none rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-primary outline-none"
                  placeholder="Enter Fingerprint ID"
                />
                <button onClick={handleSaveFingerprint} disabled={savingFingerprint} className="p-1.5 bg-primary text-on-primary rounded hover:opacity-90">
                  <Check className="w-4 h-4" />
                </button>
                <button onClick={() => setIsEditingFingerprint(false)} className="p-1.5 bg-surface-container-high text-on-surface rounded hover:bg-surface-container-highest">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <span className="font-mono bg-surface-container-highest px-3 py-1 rounded text-sm">
                  {driver.fingerprint_id || "Not set"}
                </span>
                <button onClick={() => setIsEditingFingerprint(true)} className="text-primary hover:underline text-sm flex items-center gap-1">
                  <Edit2 className="w-3 h-3" /> Edit
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        {/* Driving Sessions */}
        <div className="flex flex-col gap-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary" /> Timekeeping History
          </h3>
          <div className="bg-surface-container rounded-xl overflow-hidden">
            {loadingHistory ? (
              <div className="p-4 text-center text-secondary text-sm">Loading...</div>
            ) : sessions.length === 0 ? (
              <div className="p-4 text-center text-secondary text-sm">No driving sessions found.</div>
            ) : (
              <div className="flex flex-col divide-y divide-surface-container-high max-h-[400px] overflow-y-auto">
                {sessions.map(session => (
                  <div key={session.id} className="p-4 flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold">{new Date(session.started_at).toLocaleString('en-GB', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                      {session.status === "ACTIVE" ? (
                        <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded">ACTIVE</span>
                      ) : (
                        <span className="text-xs font-bold text-secondary bg-surface-container-high px-2 py-0.5 rounded">COMPLETED</span>
                      )}
                    </div>
                    {session.ended_at && (
                      <span className="text-xs text-secondary">Ended: {new Date(session.ended_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Violations */}
        <div className="flex flex-col gap-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-error" /> Violation History
          </h3>
          <div className="bg-surface-container rounded-xl overflow-hidden">
            {loadingHistory ? (
              <div className="p-4 text-center text-secondary text-sm">Loading...</div>
            ) : alerts.length === 0 ? (
              <div className="p-4 text-center text-secondary text-sm">No violations found.</div>
            ) : (
              <div className="flex flex-col divide-y divide-surface-container-high max-h-[400px] overflow-y-auto">
                {alerts.map(alert => (
                  <div key={alert.id} className="p-4 flex flex-col gap-2 hover:bg-surface-container-low transition-colors group">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-col gap-1 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-error">{alert.alertType.replace("_", " ")}</span>
                          <span className="text-[10px] font-bold text-secondary bg-surface-container-highest px-1.5 rounded uppercase">{alert.status}</span>
                        </div>
                        <span className="text-xs text-secondary">{new Date(alert.createdAt).toLocaleString('en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <button 
                        onClick={() => navigate(`/alerts/${alert.id}`)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 bg-primary/10 text-primary rounded-lg transition-all hover:bg-primary/20 shrink-0"
                        title="View Incident Details"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-sm text-on-surface line-clamp-2">{alert.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Edit Profile Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b border-surface-container-high shrink-0">
              <h2 className="text-xl font-bold">Edit Driver Profile</h2>
              <button onClick={() => setIsEditModalOpen(false)} className="p-2 hover:bg-surface-container-low rounded-full">
                <X className="w-5 h-5 text-secondary" />
              </button>
            </div>
            <form onSubmit={handleSaveProfile} className="p-6 flex flex-col gap-4 overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Full Name</label>
                  <input
                    type="text"
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="John Doe"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Avatar URL</label>
                  <input
                    type="url"
                    value={editAvatar}
                    onChange={e => setEditAvatar(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="https://example.com/avatar.jpg"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Date of Birth</label>
                  <input
                    type="date"
                    value={editBirthday}
                    onChange={e => setEditBirthday(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Gender</label>
                  <select
                    value={editGender}
                    onChange={e => setEditGender(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                  >
                    <option value="">Select Gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">City</label>
                  <input
                    type="text"
                    value={editCity}
                    onChange={e => setEditCity(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="Da Nang"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-surface-container-high">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-4 py-2 rounded-lg font-bold text-secondary hover:bg-surface-container-high"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingProfile}
                  className="px-4 py-2 rounded-lg font-bold bg-primary text-on-primary hover:opacity-90 disabled:opacity-50"
                >
                  {isSavingProfile ? "Saving..." : "Save Profile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
