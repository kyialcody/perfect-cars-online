import { apiFetch } from "./client";
import type { Money } from "./types";

export type PartCondition = "new" | "used";
export type PartKind = "original" | "aftermarket";
export type PartSort = "newest" | "price_asc" | "price_desc";

export interface PartListItem {
  id: number;
  slug: string;
  name: string;
  condition: PartCondition;
  kind: PartKind;
  category: string | null;
  category_slug: string | null;
  brand: string | null;
  brand_slug: string | null;
  manufacturer: string | null;
  part_number: string | null;
  price: Money;
  price_old: Money | null;
  benefit_badge: string | null;
  status_text: string | null;
  in_stock: boolean;
  qty: number;
  image_url: string | null;
}

export interface PartListResponse {
  items: PartListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PartImageOut {
  url: string | null;
  is_main: boolean;
  sort_order: number;
}

export interface PartDetail extends PartListItem {
  description: string | null;
  images: PartImageOut[];
  similar: PartListItem[];
}

export interface PartRefOption {
  slug: string;
  name: string;
}

export interface PartBrandOption {
  slug: string;
  name: string;
  logo_url: string | null;
}

export interface PartEnumOption {
  value: string;
  name: string;
}

export interface PartFiltersResponse {
  categories: PartRefOption[];
  brands: PartBrandOption[];
  manufacturers: string[];
  conditions: PartEnumOption[];
  kinds: PartEnumOption[];
}

export interface PartsQuery {
  page?: number;
  page_size?: number;
  sort?: PartSort;
  category?: string;
  brand?: string;
  condition?: PartCondition;
  kind?: PartKind;
  manufacturer?: string;
  price_min?: number;
  price_max?: number;
  in_stock?: boolean;
  q?: string;
}

function toQueryString(params: object): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  return qs.toString();
}

export function listParts(params: PartsQuery = {}): Promise<PartListResponse> {
  const qs = toQueryString(params);
  return apiFetch<PartListResponse>(`/parts${qs ? `?${qs}` : ""}`);
}

export function getPartFilters(): Promise<PartFiltersResponse> {
  return apiFetch<PartFiltersResponse>("/parts/filters");
}

export function getPart(slug: string): Promise<PartDetail> {
  return apiFetch<PartDetail>(`/parts/${encodeURIComponent(slug)}`);
}
