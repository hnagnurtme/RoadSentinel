import {
    createContext,
    useCallback,
    useContext,
    useMemo,
    useState,
    type ReactNode,
    useEffect,
  } from "react";
  import { env } from "@/config/env";
  import type { UserProfile } from "@/types/user";
  import { mapUserFromApi } from "@/types/user";
  import {
    clearSession,
    loadStoredToken,
    loadStoredUserJson,
    persistSession,
    registerAuthTokenGetter,
  } from "@/auth/session";
  
  interface AuthState {
    token: string | null;
    user: UserProfile | null;
  }
  
  interface AuthContextValue extends AuthState {
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    setSession: (token: string, user: UserProfile) => void;
  }
  
  const AuthContext = createContext<AuthContextValue | null>(null);
  
  function parseStoredUser(): UserProfile | null {
    const raw = loadStoredUserJson();
    if (!raw) return null;
    try {
      return mapUserFromApi(JSON.parse(raw) as Record<string, unknown>);
    } catch {
      return null;
    }
  }
  
  export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(() => loadStoredToken());
    const [user, setUser] = useState<UserProfile | null>(() => parseStoredUser());
  
    const setSession = useCallback((nextToken: string, nextUser: UserProfile) => {
      setToken(nextToken);
      setUser(nextUser);
      persistSession(nextToken, JSON.stringify({ ...nextUser, _id: nextUser.id }));
    }, []);
  
    const login = useCallback(
      async (email: string, password: string) => {
        const res = await fetch(`${env.apiBaseUrl}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const json = (await res.json()) as {
          success?: boolean;
          data?: { access_token: string; user: Record<string, unknown> };
          message?: string;
        };
        if (!res.ok || !json.success || !json.data?.access_token || !json.data?.user) {
          throw new Error(json.message || "Đăng nhập thất bại");
        }
        const u = mapUserFromApi(json.data.user);
        setSession(json.data.access_token, u);
      },
      [setSession]
    );
  
    const logout = useCallback(() => {
      clearSession();
      setToken(null);
      setUser(null);
    }, []);
  
    useEffect(() => {
        registerAuthTokenGetter(() => token);
      }, [token]);
  
    const value = useMemo(
      () => ({ token, user, login, logout, setSession }),
      [token, user, login, logout, setSession]
    );
  
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
  }
  
  export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
  }