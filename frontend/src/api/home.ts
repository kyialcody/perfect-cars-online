import { apiFetch } from "./client";
import type {
  AboutPage,
  ContactPage,
  DealerLocation,
  HomeCollection,
  HomeContentResponse,
} from "./types";

export function getHomeContent(): Promise<HomeContentResponse> {
  return apiFetch<HomeContentResponse>("/home");
}

export function getCollections(): Promise<HomeCollection[]> {
  return apiFetch<HomeCollection[]>("/home/collections");
}

export function getAboutPage(): Promise<AboutPage> {
  return apiFetch<AboutPage>("/home/about");
}

export function getLocations(): Promise<DealerLocation[]> {
  return apiFetch<DealerLocation[]>("/home/locations");
}

export function getContactsPage(): Promise<ContactPage> {
  return apiFetch<ContactPage>("/home/contacts");
}
