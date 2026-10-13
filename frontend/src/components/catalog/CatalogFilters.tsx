import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { CatalogQuery } from "../../api/catalog";
import type { FiltersResponse, RefOption } from "../../api/types";
import PriceRange from "./PriceRange";
import "./catalog-filters.css";

type FilterKey =
  | "model"
  | "body_type"
  | "transmission"
  | "drive"
  | "engine_type"
  | "condition";

const CONDITIONS: { value: "" | "new" | "used"; label: string }[] = [
  { value: "", label: "Все" },
  { value: "new", label: "Новые" },
  { value: "used", label: "С пробегом" },
];

export default function CatalogFilters({
  opts,
  params,
  onParam,
  onPrice,
  onReset,
  hasActiveFilters,
  lockCondition = false,
  simple = false,
  onShow,
}: {
  opts: FiltersResponse | null;
  params: CatalogQuery;
  onParam: (key: FilterKey | "year_min" | "year_max" | "mileage_max", value: string) => void;
  onPrice: (min: number | undefined, max: number | undefined) => void;
  onReset: () => void;
  hasActiveFilters: boolean;
  // On the dedicated «Авто с пробегом» route the condition is fixed, so the
  // Все/Новые/С пробегом tabs are hidden.
  lockCondition?: boolean;
  // Compact «быстрый подбор» layout (used route): only тип кузова + коробка +
  // price + a «Показать» button, matching the reference.
  simple?: boolean;
  onShow?: () => void;
}) {
  const navigate = useNavigate();
  // Models depend on the chosen brand (brand lives in the sidebar).
  const models = useMemo(() => {
    if (!opts) return [];
    return params.brand
      ? opts.models.filter((m) => m.brand_slug === params.brand)
      : opts.models;
  }, [opts, params.brand]);

  const isUsed = params.condition === "used";

  const select = (
    key: FilterKey,
    label: string,
    options: RefOption[],
    anyLabel: string,
  ) => (
    <label className="catalog-filters__field">
      <span>{label}</span>
      <select value={(params[key] as string) ?? ""} onChange={(e) => onParam(key, e.target.value)}>
        <option value="">{anyLabel}</option>
        {options.map((o) => (
          <option key={o.slug} value={o.slug}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="catalog-filters">
      {!lockCondition && (
        <div className="catalog-filters__conditions" role="group" aria-label="Состояние">
          {CONDITIONS.map((c) => (
            <button
              key={c.value || "all"}
              type="button"
              className={`catalog-filters__tab${(params.condition ?? "") === c.value ? " is-active" : ""}`}
              aria-pressed={(params.condition ?? "") === c.value}
              // «С пробегом» is its own page now — go there instead of just
              // filtering the catalog in place.
              onClick={() =>
                c.value === "used" ? navigate("/used") : onParam("condition", c.value)
              }
            >
              {c.label}
            </button>
          ))}
        </div>
      )}

      <div className="catalog-filters__grid">
        {simple ? (
          <>
            {select("body_type", "Тип кузова", opts?.body_types ?? [], "Любой")}
            {select("transmission", "Коробка передач", opts?.transmissions ?? [], "Любая")}
          </>
        ) : (
          <>
        {select("model", "Модель", models, "Любая")}
        {select("body_type", "Тип кузова", opts?.body_types ?? [], "Любой")}
        {select("transmission", "Коробка передач", opts?.transmissions ?? [], "Любая")}
        {select("drive", "Привод", opts?.drives ?? [], "Любой")}
        {select("engine_type", "Тип двигателя", opts?.engine_types ?? [], "Любой")}

        {isUsed && (
          <>
            <div className="catalog-filters__pair">
              <label className="catalog-filters__field">
                <span>Год от</span>
                <input
                  type="number"
                  inputMode="numeric"
                  min={1900}
                  placeholder="от"
                  value={params.year_min ?? ""}
                  onChange={(e) => onParam("year_min", e.target.value)}
                />
              </label>
              <label className="catalog-filters__field">
                <span>Год до</span>
                <input
                  type="number"
                  inputMode="numeric"
                  min={1900}
                  placeholder="до"
                  value={params.year_max ?? ""}
                  onChange={(e) => onParam("year_max", e.target.value)}
                />
              </label>
            </div>
            <label className="catalog-filters__field">
              <span>Пробег до, км</span>
              <input
                type="number"
                inputMode="numeric"
                min={0}
                placeholder="любой"
                value={params.mileage_max ?? ""}
                onChange={(e) => onParam("mileage_max", e.target.value)}
              />
            </label>
          </>
        )}
          </>
        )}
      </div>

      <PriceRange min={params.price_min} max={params.price_max} onCommit={onPrice} />

      {simple ? (
        <button
          type="button"
          className="btn btn--primary catalog-filters__show"
          onClick={onShow}
        >
          Показать
        </button>
      ) : (
        hasActiveFilters && (
          <button type="button" className="catalog-filters__reset" onClick={onReset}>
            Сбросить фильтры
          </button>
        )
      )}
    </div>
  );
}
