import type { PartCondition, PartKind, PartsQuery, PartSort } from "../api/parts";

export const PART_CONDITION_LABEL: Record<PartCondition, string> = {
  new: "Новая",
  used: "Б/У",
};
export const PART_KIND_LABEL: Record<PartKind, string> = {
  original: "Оригинал",
  aftermarket: "Аналог",
};

// Upper bound for the parts price slider. Parts above this still show — the
// slider just maxes out here. Much smaller than the car slider.
export const PARTS_PRICE_MAX = 300_000;
export const PARTS_PRICE_STEP = 1_000;

export const PARTS_SORT_OPTIONS: { value: PartSort; label: string }[] = [
  { value: "newest", label: "Сначала новые" },
  { value: "price_asc", label: "Сначала дешевле" },
  { value: "price_desc", label: "Сначала дороже" },
];

const SORT_VALUES = new Set(PARTS_SORT_OPTIONS.map((o) => o.value));

function num(sp: URLSearchParams, key: string): number | undefined {
  const raw = sp.get(key);
  if (raw === null || raw === "") return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

/**
 * Read the parts query from URL search params. The URL is the single source of
 * truth for filters/sort, so a shared link reproduces the same view.
 */
export function parsePartsParams(sp: URLSearchParams): PartsQuery {
  const opt = (key: string) => sp.get(key) || undefined;
  const cond = sp.get("condition");
  const kind = sp.get("kind");
  const sort = sp.get("sort");
  return {
    sort: sort && SORT_VALUES.has(sort as never) ? (sort as PartSort) : "newest",
    category: opt("category"),
    brand: opt("brand"),
    condition: cond === "new" || cond === "used" ? cond : undefined,
    kind: kind === "original" || kind === "aftermarket" ? kind : undefined,
    manufacturer: opt("manufacturer"),
    price_min: num(sp, "price_min"),
    price_max: num(sp, "price_max"),
  };
}
