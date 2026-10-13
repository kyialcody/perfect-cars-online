// Проект работает на двух доменах с разными юридическими реквизитами:
//   perfect-cars.online   — Россия
//   auto-america.online   — не Россия
// Тексты соглашений идентичны и отличаются только доменом и почтой, поэтому
// бренд хранит именно эти два поля, а страницы соглашений их подставляют.

export type BrandId = "perfect-cars" | "auto-america";

export type Brand = {
  id: BrandId;
  domain: string;
  email: string;
  region: "ru" | "intl";
};

const BRANDS: Record<BrandId, Brand> = {
  "perfect-cars": {
    id: "perfect-cars",
    domain: "perfect-cars.online",
    email: "info@perfect-cars.online",
    region: "ru",
  },
  "auto-america": {
    id: "auto-america",
    domain: "auto-america.online",
    email: "info@auto-america.online",
    region: "intl",
  },
};

function isBrandId(value: unknown): value is BrandId {
  return value === "perfect-cars" || value === "auto-america";
}

const envBrand = import.meta.env.VITE_BRAND;
const DEFAULT_BRAND: BrandId = isBrandId(envBrand) ? envBrand : "perfect-cars";

const STORAGE_KEY = "brand";

// Реальные домены всегда определяют бренд по hostname. На localhost / preview
// (где домена нет) можно переключаться через ?brand=... — выбор запоминается,
// чтобы проверять оба варианта. VITE_BRAND задаёт дефолт сборки.
function resolveBrandId(): BrandId {
  if (typeof window === "undefined") return DEFAULT_BRAND;

  const host = window.location.hostname;
  if (host.includes("auto-america")) return "auto-america";
  if (host.includes("perfect-cars")) return "perfect-cars";

  const override = new URLSearchParams(window.location.search).get("brand");
  if (isBrandId(override)) {
    try {
      window.localStorage.setItem(STORAGE_KEY, override);
    } catch {
      /* private mode / storage disabled — не критично */
    }
    return override;
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isBrandId(stored)) return stored;
  } catch {
    /* ignore */
  }

  return DEFAULT_BRAND;
}

// Бренд не меняется в течение сессии, поэтому вычисляем один раз при загрузке.
export const brand: Brand = BRANDS[resolveBrandId()];

export function getBrand(): Brand {
  return brand;
}
