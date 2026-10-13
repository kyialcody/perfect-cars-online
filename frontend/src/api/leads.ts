import { apiFetch } from "./client";
import type { LeadStatus } from "./profile";

export interface LeadPayload {
  name: string;
  phone: string;
  source?: "catalog" | "car_detail" | "quick_pick" | "footer" | "other";
  source_title: string;
  dedupe_key: string;
  car_id?: number | null;
  comment?: string | null;
  consent: boolean;
}

export interface LeadOut {
  id: number;
  user_id: number | null;
  name: string;
  phone: string;
  source: string;
  source_title: string | null;
  dedupe_key: string | null;
  car_id: number | null;
  booking_id: number | null;
  comment: string | null;
  status: LeadStatus;
  created_at: string;
}

export function createLead(payload: LeadPayload) {
  return apiFetch<LeadOut>("/leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
