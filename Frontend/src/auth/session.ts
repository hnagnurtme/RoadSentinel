const TOKEN_KEY = "rs_access_token";
const USER_KEY = "rs_user";

export function loadStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function loadStoredUserJson(): string | null {
  return sessionStorage.getItem(USER_KEY);
}

export function persistSession(token: string, userJson: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, userJson);
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

let tokenGetter: (() => string | null) | null = null;

export function registerAuthTokenGetter(fn: () => string | null): void {
  tokenGetter = fn;
}

export function getAuthToken(): string | null {
  return tokenGetter?.() ?? null;
}