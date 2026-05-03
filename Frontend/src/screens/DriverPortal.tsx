import { useEffect, useState } from "react";
import { CalendarDays, Mail, MapPin, UserRound } from "lucide-react";
import { env } from "@/config/env";
import { useAuth } from "@/auth/AuthContext";
import { DriverHeader } from "@/components/DriverHeader";
import type { UserProfile } from "@/types/user";
import { mapUserFromApi } from "@/types/user";
import type { ApiEnvelope } from "@/api/http";

function displayName(u: UserProfile): string {
  const n = [u.name__given, u.name__family].filter(Boolean).join(" ");
  return (u.name || n || u.email || "Driver").trim();
}

export function DriverPortal() {
  const { token } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetch(`${env.apiBaseUrl}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        const j = (await r.json()) as ApiEnvelope<Record<string, unknown>>;
        if (!r.ok || !j.success || !j.data) throw new Error(j.message || "Unable to load profile");
        return mapUserFromApi(j.data);
      })
      .then((p) => {
        if (!cancelled) setProfile(p);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

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
            <section className="lg:col-span-8 bg-surface-container-lowest p-6 rounded-xl ring-1 ring-outline-variant/15 shadow-sm space-y-4">
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
                <div className="min-w-0">
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
    </>
  );
}