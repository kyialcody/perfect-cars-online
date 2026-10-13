import type { Money } from "../api/types";

// Currency is a placeholder for the MVP (see ТЗ open question) — rubles for now.
const CURRENCY = "₽";

function toNumber(value: Money | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isNaN(n) ? null : n;
}

/** Grouped price with the currency sign appended, e.g. 1615000 -> "1 615 000 ₽". */
export function formatPrice(value: Money | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "";
  return `${n.toLocaleString("ru-RU")} ${CURRENCY}`;
}

/** Plain grouped number, no currency (e.g. mileage). */
export function formatNumber(value: Money | null | undefined): string {
  const n = toNumber(value);
  return n === null ? "" : n.toLocaleString("ru-RU");
}
