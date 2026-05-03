import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import type { UserRole } from "@/types/user";

export function RequireRole({ role }: { role: UserRole }) {
  const { user } = useAuth();
  const loc = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }
  if (user.role !== role) {
    return <Navigate to={user.role === "admin" ? "/dashboard" : "/driver"} replace />;
  }
  return <Outlet />;
}