import { apiFetch } from "./client";
import type { CarDetail, CarListResponse, CountResponse, FiltersResponse } from "./types";

export interface CatalogQuery {
  page?: number;
  page_size?: number;
  sort?: "newest" | "price_asc" | "price_desc" | "year_desc";
  // filters (slugs) — shared by list and count
  brand?: string;
  model?: string;
  body_type?: string;
  transmission?: string;
  drive?: string;
  engine_type?: string;
  condition?: "new" | "used" | "special";
  q?: string;
  year_min?: number;
  year_max?: number;
  price_min?: number;
  price_max?: number;
  mileage_max?: number;
}

export function toQueryString(params: object): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  return qs.toString();
}

export function listCars(params: CatalogQuery = {}): Promise<CarListResponse> {
  const qs = toQueryString(params);
  return apiFetch<CarListResponse>(`/cars${qs ? `?${qs}` : ""}`);
}

export function countCars(params: CatalogQuery = {}): Promise<CountResponse> {
  const qs = toQueryString(params);
  return apiFetch<CountResponse>(`/cars/count${qs ? `?${qs}` : ""}`);
}

export function getCar(slug: string): Promise<CarDetail> {
  return apiFetch<CarDetail>(`/cars/${encodeURIComponent(slug)}`);
}

export function getFilters(): Promise<FiltersResponse> {
  return apiFetch<FiltersResponse>("/catalog/filters");
}
