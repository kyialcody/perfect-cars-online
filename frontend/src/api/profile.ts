import { apiFetch } from "./client";
import type { UserOut } from "./auth";

export type LeadStatus = "new" | "in_progress" | "approved" | "rejected" | "done";

export interface ProfileCar {
  id: number;
  slug: string;
  title: string;
  image_url: string | null;
}

export interface ProfileLead {
  id: number;
  source_title: string | null;
  dedupe_key: string | null;
  status: LeadStatus;
  comment: string | null;
  phone: string;
  created_at: string;
  car: ProfileCar | null;
}

export function updateProfile(payload: { full_name: string | null; phone: string | null }) {
  return apiFetch<UserOut>("/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function changePassword(payload: { current_password: string; new_password: string }) {
  return apiFetch<void>("/profile/password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listProfileLeads() {
  return apiFetch<ProfileLead[]>("/profile/leads");
}
