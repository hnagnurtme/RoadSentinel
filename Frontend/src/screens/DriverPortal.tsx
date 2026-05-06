import React, { useEffect, useState } from "react";
import { CalendarDays, Mail, MapPin, UserRound, Edit2, X } from "lucide-react";
import { env } from "@/config/env";
import { useAuth } from "@/auth/AuthContext";
import { DriverHeader } from "@/components/DriverHeader";
import type { UserProfile } from "@/types/user";
import { mapUserFromApi } from "@/types/user";
import type { ApiEnvelope } from "@/api/http";
import { updateUser } from "@/api/users";

function displayName(u: UserProfile): string {
  const n = [u.name__given, u.name__family].filter(Boolean).join(" ");
  return (u.name || n || u.email || "Driver").trim();
}

export function DriverPortal() {
  const { token } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editGivenName, setEditGivenName] = useState("");
  const [editFamilyName, setEditFamilyName] = useState("");
  const [editAvatar, setEditAvatar] = useState("");
  const [editBirthday, setEditBirthday] = useState("");
  const [editGender, setEditGender] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editCountry, setEditCountry] = useState("");
  const [editAddressLine1, setEditAddressLine1] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const fetchProfile = () => {
    if (!token) return;
    fetch(`${env.apiBaseUrl}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        const j = (await r.json()) as ApiEnvelope<Record<string, unknown>>;
        if (!r.ok || !j.success || !j.data) throw new Error(j.message || "Unable to load profile");
        return mapUserFromApi(j.data);
      })
      .then((p) => {
        setProfile(p);
        setEditGivenName(p.name__given || "");
        setEditFamilyName(p.name__family || "");
        setEditAvatar(p.avatar_image_url || "");
        setEditBirthday(p.birthday || "");
        setEditGender(p.gender || "");
        setEditCity(p.address__city || "");
        setEditCountry(p.address__country || "");
        setEditAddressLine1(p.address__line1 || "");
      })
      .catch((e: Error) => {
        setError(e.message);
      });
  };

  useEffect(() => {
    fetchProfile();
  }, [token]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setIsSavingProfile(true);
    try {
      await updateUser(profile.id, {
        name__given: editGivenName || null,
        name__family: editFamilyName || null,
        avatar_image_url: editAvatar || null,
        birthday: editBirthday || null,
        gender: editGender || null,
        address__city: editCity || null,
        address__country: editCountry || null,
        address__line1: editAddressLine1 || null,
      });
      setIsEditModalOpen(false);
      fetchProfile();
    } catch (err) {
      console.error("Failed to update profile", err);
      alert("Failed to update profile.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  return (
    <>
      <DriverHeader />
      <div className="p-10 max-w-[1200px] space-y-8">
        <div>
          <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface-variant block mb-2">
            Driver dossier
          </span>
          <h2 className="text-3xl font-black text-primary tracking-tight">My Profile</h2>
          <p className="text-secondary text-sm mt-1 font-medium">Your driver identity information in the RoadSentinel system.</p>
        </div>

        {error && (
          <div className="text-sm font-semibold bg-error-container text-on-error-container px-4 py-3 rounded-xl">{error}</div>
        )}

        {!profile && !error && (
          <p className="text-secondary text-sm">Loading profile...</p>
        )}

        {profile && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <section className="lg:col-span-8 bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm space-y-4 relative">
              <button
                onClick={() => {
                  setEditGivenName(profile.name__given || "");
                  setEditFamilyName(profile.name__family || "");
                  setEditAvatar(profile.avatar_image_url || "");
                  setEditBirthday(profile.birthday || "");
                  setEditGender(profile.gender || "");
                  setEditCity(profile.address__city || "");
                  setEditCountry(profile.address__country || "");
                  setEditAddressLine1(profile.address__line1 || "");
                  setIsEditModalOpen(true);
                }}
                className="absolute top-6 right-6 p-2 rounded-lg bg-surface-container text-secondary hover:text-primary transition-colors flex items-center gap-2 text-sm font-semibold pr-3"
                title="Edit Profile"
              >
                <Edit2 className="w-4 h-4" /> Edit
              </button>
              <div className="flex items-start gap-6">
                {profile.avatar_image_url ? (
                  <img
                    src={profile.avatar_image_url}
                    alt=""
                    className="w-28 h-28 rounded-xl object-cover ring-1 ring-outline-variant/30"
                  />
                ) : (
                  <div className="w-28 h-28 rounded-xl bg-primary text-on-primary flex items-center justify-center font-black text-2xl">
                    {displayName(profile).slice(0, 2).toUpperCase()}
                  </div>
                )}
                <div className="min-w-0 pr-24">
                  <h3 className="text-2xl font-black text-primary truncate">{displayName(profile)}</h3>
                  <p className="text-sm text-secondary flex items-center gap-2 mt-2">
                    <Mail className="w-4 h-4 shrink-0" />
                    {profile.email}
                  </p>
                  <span className="inline-block mt-3 text-[10px] font-black uppercase tracking-widest bg-surface-container-high text-primary px-3 py-1 rounded-full">
                    Role: driver
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-outline-variant/15">
                <div className="bg-surface-container-low p-4 rounded-lg">
                  <p className="text-[10px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center gap-2">
                    <UserRound className="w-4 h-4" /> Gender
                  </p>
                  <p className="text-sm font-semibold text-primary">{profile.gender ?? "—"}</p>
                </div>
                <div className="bg-surface-container-low p-4 rounded-lg">
                  <p className="text-[10px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center gap-2">
                    <CalendarDays className="w-4 h-4" /> Date of birth
                  </p>
                  <p className="text-sm font-semibold text-primary">{profile.birthday ?? "—"}</p>
                </div>
                <div className="bg-surface-container-low p-4 rounded-lg md:col-span-2">
                  <p className="text-[10px] font-bold uppercase text-secondary tracking-wider mb-1 flex items-center gap-2">
                    <MapPin className="w-4 h-4" /> Address
                  </p>
                  <p className="text-sm font-semibold text-primary">
                    {[profile.address__line1, profile.address__line2, profile.address__city, profile.address__country]
                      .filter(Boolean)
                      .join(", ") || "-"}
                  </p>
                </div>
              </div>
            </section>
            <section className="lg:col-span-4 bg-primary text-white p-6 rounded-xl shadow-sm flex flex-col justify-between">
              <div>
                <p className="text-[10px] font-bold opacity-70 uppercase tracking-widest">Identity ID</p>
                <p className="text-lg font-mono mt-2 break-all">{profile.id}</p>
              </div>
              <p className="text-xs text-white/80 mt-6">
                Use the Violation Evidence tab to review incidents linked to your account.
              </p>
            </section>
          </div>
        )}
      </div>

      {/* Edit Profile Modal */}
      {isEditModalOpen && profile && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b border-surface-container-high shrink-0">
              <h2 className="text-xl font-bold">Edit Profile</h2>
              <button onClick={() => setIsEditModalOpen(false)} className="p-2 hover:bg-surface-container-low rounded-full">
                <X className="w-5 h-5 text-secondary" />
              </button>
            </div>
            <form onSubmit={handleSaveProfile} className="p-6 flex flex-col gap-4 overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Given Name</label>
                  <input
                    type="text"
                    value={editGivenName}
                    onChange={e => setEditGivenName(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="John"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Family Name</label>
                  <input
                    type="text"
                    value={editFamilyName}
                    onChange={e => setEditFamilyName(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="Doe"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2 col-span-2">
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
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Country</label>
                  <input
                    type="text"
                    value={editCountry}
                    onChange={e => setEditCountry(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="Vietnam"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-bold text-secondary">Address Line 1</label>
                  <input
                    type="text"
                    value={editAddressLine1}
                    onChange={e => setEditAddressLine1(e.target.value)}
                    className="bg-surface-container border border-surface-container-highest rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary outline-none"
                    placeholder="123 Example St"
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
    </>
  );
}