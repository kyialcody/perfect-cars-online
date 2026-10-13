// Mirrors backend app/schemas/catalog.py. Decimal fields arrive as strings
// (pydantic JSON), so money/number fields are typed `number | string`.

export type Money = number | string;

export interface ColorOut {
  name: string;
  hex: string;
  image_url: string | null;
}

export interface CarListItem {
  id: number;
  slug: string;
  condition: "new" | "used" | "special";
  brand: string;
  brand_slug: string;
  model: string;
  model_slug: string;
  title: string;

  price: Money;
  price_old: Money | null;
  benefit_badge: string | null;
  status_text: string | null;

  power_hp: number | null;
  fuel_consumption: Money | null; // electric, kWh
  fuel_consumption_petrol: Money | null; // petrol, L/100 km
  acceleration_0_100: Money | null;
  max_speed: number | null;

  year: number | null;
  mileage: number | null;
  engine_volume: Money | null; // used cars, L

  body_type: string | null;
  engine_type: string | null;
  drive: string | null; // used cars
  transmission: string | null; // used cars

  in_stock: boolean;
  qty: number;
  is_promo: boolean;

  image_url: string | null;
  colors: ColorOut[];
}

export interface CarListResponse {
  items: CarListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ImageOut {
  url: string;
  is_main: boolean;
  sort_order: number;
}

export interface TrimOut {
  id: number;
  name: string;
  engine_volume: Money | null;
  power_hp: number | null;
  transmission: string | null;
  drive: string | null;
  price: Money;
  price_discount: Money | null;
  sort_order: number;
  image_url: string | null;
}

export interface BenefitOut {
  icon: string;
  text: string;
  sort_order: number;
}

export interface FeatureGroup {
  block: string;
  items: string[];
}

export interface CarDetail extends CarListItem {
  images: ImageOut[];
  trims: TrimOut[];
  benefits: BenefitOut[];
  features: FeatureGroup[];
  gifts: string[];
  similar: CarListItem[];
}

export interface RefOption {
  slug: string;
  name: string;
}

export interface BrandOption {
  slug: string;
  name: string;
  logo_url: string | null;
}

export interface ModelOption {
  slug: string;
  name: string;
  brand_slug: string;
}

export interface FiltersResponse {
  brands: BrandOption[];
  models: ModelOption[];
  body_types: RefOption[];
  transmissions: RefOption[];
  drives: RefOption[];
  engine_types: RefOption[];
}

export interface CountResponse {
  count: number;
}

export interface HomePromo {
  id: number;
  image_url: string | null;
  link_url: string | null;
}

export interface HomeCollection {
  id: number;
  title: string;
  description: string | null;
  button_text: string | null;
  button_url: string | null;
  image_url: string | null;
  car: CarListItem | null;
}

export interface HomeAbout {
  description: string | null;
  video_url: string | null;
}

export interface AboutSalonPhoto {
  id: number;
  image_url: string | null;
  alt: string | null;
}

export interface BankPartner {
  id: number;
  name: string;
  logo_url: string | null;
}

export interface AboutPage {
  description: string | null;
  page_text: string | null;
  photos: AboutSalonPhoto[];
  banks: BankPartner[];
}

export interface HomeContentResponse {
  promos: HomePromo[];
  collections: HomeCollection[];
  about: HomeAbout | null;
}

export interface DealerLocation {
  id: number;
  name: string;
  address: string;
  lat: number;
  lng: number;
  phone: string | null;
  hours: string | null;
}

export interface ContactPhone {
  id: number;
  value: string;
}

export interface ContactAddress {
  id: number;
  value: string;
  show_in_header: boolean;
}

export interface ContactPhoto {
  id: number;
  image_url: string | null;
  alt: string | null;
}

export interface Requisite {
  id: number;
  label: string;
  value: string;
}

export interface SocialLink {
  id: number;
  kind: string;
  url: string | null;
  icon_url: string | null;
}

export interface ContactPage {
  about_text: string | null;
  footer_about_text: string | null;
  phones: ContactPhone[];
  addresses: ContactAddress[];
  photos: ContactPhoto[];
  requisites: Requisite[];
  socials: SocialLink[];
}
