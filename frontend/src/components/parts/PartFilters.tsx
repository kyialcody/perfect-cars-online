import type { PartsQuery, PartFiltersResponse } from "../../api/parts";
import PriceRange from "../catalog/PriceRange";
import { PARTS_PRICE_MAX, PARTS_PRICE_STEP } from "../../lib/partsParams";
import "../catalog/catalog-filters.css";

type SelectKey = "category" | "condition" | "kind" | "manufacturer";

// Compact «быстрый подбор» filters for the parts page, matching the used-car
// reference: a few selects + price slider + «Показать». Reuses catalog-filters.css.
export default function PartFilters({
  opts,
  params,
  onParam,
  onPrice,
  onShow,
}: {
  opts: PartFiltersResponse | null;
  params: PartsQuery;
  onParam: (key: SelectKey, value: string) => void;
  onPrice: (min: number | undefined, max: number | undefined) => void;
  onShow: () => void;
}) {
  const select = (
    key: SelectKey,
    label: string,
    anyLabel: string,
    options: { value: string; name: string }[],
  ) => (
    <label className="catalog-filters__field">
      <span>{label}</span>
      <select
        value={(params[key] as string) ?? ""}
        onChange={(e) => onParam(key, e.target.value)}
      >
        <option value="">{anyLabel}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );

  const categories = (opts?.categories ?? []).map((c) => ({ value: c.slug, name: c.name }));
  const conditions = opts?.conditions ?? [];
  const kinds = opts?.kinds ?? [];
  const manufacturers = (opts?.manufacturers ?? []).map((m) => ({ value: m, name: m }));

  return (
    <div className="catalog-filters">
      <div className="catalog-filters__grid">
        {select("category", "Категория", "Любая", categories)}
        {select("condition", "Состояние", "Любое", conditions)}
        {select("kind", "Тип", "Любой", kinds)}
        {select("manufacturer", "Производитель", "Любой", manufacturers)}
      </div>

      <PriceRange
        min={params.price_min}
        max={params.price_max}
        onCommit={onPrice}
        priceMax={PARTS_PRICE_MAX}
        priceStep={PARTS_PRICE_STEP}
      />

      <button type="button" className="btn btn--primary catalog-filters__show" onClick={onShow}>
        Показать
      </button>
    </div>
  );
}
