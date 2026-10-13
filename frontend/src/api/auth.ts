import { apiFetch, storeTokens, clearTokens } from "./client";

export interface UserOut {
  id: number;
  email: string;
  full_name: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface RegisterPayload {
  full_name: string;
  phone: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function register(payload: RegisterPayload): Promise<UserOut> {
  return apiFetch<UserOut>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<UserOut> {
  const tokens = await apiFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  storeTokens(tokens);
  return me();
}

export async function loginAfterRegister(email: string, password: string): Promise<UserOut> {
  return login({ email, password });
}

export function logout() {
  clearTokens();
}

export function me(): Promise<UserOut> {
  return apiFetch<UserOut>("/auth/me");
}
