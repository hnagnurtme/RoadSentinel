import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Radar, TriangleAlert, Route } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import type React from "react";
import { useLanguage } from "@/i18n/LanguageContext";

import { Logo } from "@/components/Logo";

export function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    navigate(user.role === "admin" ? "/dashboard" : "/driver", { replace: true });
  }, [user, navigate]);

  if (user) {
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      const u = JSON.parse(sessionStorage.getItem("rs_user") || "{}") as { role?: string };
      navigate(u.role === "admin" ? "/dashboard" : "/driver", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background font-sans">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
        <section className="bg-surface-container-lowest flex items-center justify-center p-8 md:p-12">
          <div className="w-full max-w-md space-y-8">
          <div className="flex flex-col items-center gap-2 text-center">
            <Logo className="h-24 w-auto" />
            <p className="text-sm text-secondary font-medium mt-4">
              {t("login.welcome")} - {t("login.desc")}
            </p>
          </div>

          {error && (
            <div className="text-xs font-semibold bg-error-container text-on-error-container px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={onSubmit}>
            <div>
              <label className="text-[10px] font-bold uppercase text-secondary tracking-wider">{t("login.email")}</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full px-4 py-2.5 rounded-lg border border-surface-container-high bg-surface-container-low text-sm focus:outline-none focus:ring-2 focus:ring-primary/15"
                placeholder="you@company.com"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase text-secondary tracking-wider">{t("login.password")}</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full px-4 py-2.5 rounded-lg border border-surface-container-high bg-surface-container-low text-sm focus:outline-none focus:ring-2 focus:ring-primary/15"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg bg-primary text-on-primary font-bold text-sm hover:opacity-90 disabled:opacity-60 cursor-pointer"
            >
              {loading ? t("login.signingIn") : t("login.btn")}
            </button>
          </form>
          </div>
        </section>

        <section className="relative hidden lg:flex bg-primary text-white p-10 xl:p-14 flex-col justify-between overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.28),transparent_55%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(10,37,89,0.92),rgba(10,37,89,0.76))]" />
          <div className="absolute -right-14 -top-20 w-72 h-72 rounded-full bg-white/10 blur-2xl" />
          <div className="absolute -left-20 bottom-10 w-72 h-72 rounded-full bg-white/10 blur-2xl" />
          <div className="relative z-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/70 mb-2">Operational Safety</p>
            <h2 className="text-4xl xl:text-5xl font-black leading-tight">AI-powered Driver Monitoring</h2>
            <p className="text-base text-white/85 mt-4 max-w-lg">
              Detect high-risk behavior in real time, review incident evidence, and improve fleet safety outcomes.
            </p>
          </div>

          <div className="relative z-10 mt-10 space-y-4 max-w-xl">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20 flex items-start gap-3">
              <Radar className="w-5 h-5 mt-0.5" />
              <div>
                <p className="font-bold text-sm">Live Monitoring</p>
                <p className="text-xs text-white/80">Stream camera telemetry and detect risky events instantly.</p>
              </div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20 flex items-start gap-3">
              <TriangleAlert className="w-5 h-5 mt-0.5" />
              <div>
                <p className="font-bold text-sm">Violation Evidence</p>
                <p className="text-xs text-white/80">Capture incident clips and keep a full audit trail.</p>
              </div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20 flex items-start gap-3">
              <Route className="w-5 h-5 mt-0.5" />
              <div>
                <p className="font-bold text-sm">Fleet Visibility</p>
                <p className="text-xs text-white/80">Give admins and drivers role-specific access to insights.</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}