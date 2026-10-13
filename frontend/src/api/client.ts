// Thin typed wrapper around the backend REST API.
// Base URL comes from VITE_API_URL (see .env.example), defaulting to localhost.

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const ACCESS_KEY = "cars_access_token";
const REFRESH_KEY = "cars_refresh_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface StoredTokens {
  access_token: string;
  refresh_token: string;
}

export function getStoredTokens(): StoredTokens | null {
  const access_token = localStorage.getItem(ACCESS_KEY);
  const refresh_token = localStorage.getItem(REFRESH_KEY);
  return access_token && refresh_token ? { access_token, refresh_token } : null;
}

export function storeTokens(tokens: StoredTokens) {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshTokens(): Promise<StoredTokens | null> {
  const current = getStoredTokens();
  if (!current?.refresh_token) return null;
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: current.refresh_token }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const next = (await res.json()) as StoredTokens;
  storeTokens(next);
  return next;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const tokens = getStoredTokens();
  const headers = {
    "Content-Type": "application/json",
    ...(tokens?.access_token ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
    ...(init?.headers ?? {}),
  };
  let res = await fetch(`${API_URL}${path}`, {
    headers,
    ...init,
  });
  if (res.status === 401 && !path.startsWith("/auth/")) {
    const next = await refreshTokens();
    if (next) {
      res = await fetch(`${API_URL}${path}`, {
        headers: { ...headers, Authorization: `Bearer ${next.access_token}` },
        ...init,
      });
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (body?.detail && typeof body.detail === "object") {
        const maybeMessage = (body.detail as { message?: unknown }).message;
        detail = typeof maybeMessage === "string" ? maybeMessage : JSON.stringify(body.detail);
      }
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export { API_URL };
