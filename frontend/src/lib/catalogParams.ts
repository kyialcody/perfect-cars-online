import type { CatalogQuery } from "../api/catalog";

// Upper bound for the price slider. Cars above this still
// show — the slider just maxes out here.
export const PRICE_MAX = 20_000_000;
export const PRICE_STEP = 50_000;

// Sort options offered in the catalog dropdown, in display order.
export const SORT_OPTIONS: { value: NonNullable<CatalogQuery["sort"]>; label: string }[] = [
  { value: "newest", label: "Сначала новые" },
  { value: "price_asc", label: "Сначала дешевле" },
  { value: "price_desc", label: "Сначала дороже" },
  { value: "year_desc", label: "Год: новее" },
];

const SORT_VALUES = new Set(SORT_OPTIONS.map((o) => o.value));

function num(sp: URLSearchParams, key: string): number | undefined {
  const raw = sp.get(key);
  if (raw === null || raw === "") return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

/**
 * Read the catalog query from URL search params. The URL is the single source
 * of truth for filters/sort, so a shared link reproduces the same view.
 */
export function parseCatalogParams(sp: URLSearchParams): CatalogQuery {
  const opt = (key: string) => sp.get(key) || undefined;
  const cond = sp.get("condition");
  const sort = sp.get("sort");
  return {
    sort: sort && SORT_VALUES.has(sort as never) ? (sort as CatalogQuery["sort"]) : "newest",
    brand: opt("brand"),
    model: opt("model"),
    body_type: opt("body_type"),
    transmission: opt("transmission"),
    drive: opt("drive"),
    engine_type: opt("engine_type"),
    condition: cond === "new" || cond === "used" || cond === "special" ? cond : undefined,
    year_min: num(sp, "year_min"),
    year_max: num(sp, "year_max"),
    price_min: num(sp, "price_min"),
    price_max: num(sp, "price_max"),
    mileage_max: num(sp, "mileage_max"),
  };
}
