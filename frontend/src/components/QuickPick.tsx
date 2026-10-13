import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { countCars, getFilters, toQueryString } from "../api/catalog";
import type { FiltersResponse } from "../api/types";
import { PRICE_MAX } from "../lib/catalogParams";
import "./quick-pick.css";

// Cap a typed price so we never hand the catalog an out-of-range value (which
// would push the price-slider fill bar off-screen).
function clampPrice(raw: string): string {
  if (raw === "") return "";
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return "";
  return String(Math.min(n, PRICE_MAX));
}

// «Я ищу» / quick-pick block (design: docs/design/home-top.png).
// Live «Найдено N» counter; submitting navigates to the catalog with the
// chosen filters in the URL.
type Selection = {
  brand: string;
  model: string;
  drive: string;
  transmission: string;
  engine_type: string;
  price_min: string;
  price_max: string;
};

const EMPTY: Selection = {
  brand: "",
  model: "",
  drive: "",
  transmission: "",
  engine_type: "",
  price_min: "",
  price_max: "",
};

function toQuery(sel: Selection): Record<string, string> {
  const q: Record<string, string> = {};
  if (sel.brand) q.brand = sel.brand;
  if (sel.model) q.model = sel.model;
  if (sel.drive) q.drive = sel.drive;
  if (sel.transmission) q.transmission = sel.transmission;
  if (sel.engine_type) q.engine_type = sel.engine_type;
  if (sel.price_min) q.price_min = sel.price_min;
  if (sel.price_max) q.price_max = sel.price_max;
  return q;
}

export default function QuickPick() {
  const navigate = useNavigate();
  const [opts, setOpts] = useState<FiltersResponse | null>(null);
  const [sel, setSel] = useState<Selection>(EMPTY);
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    getFilters()
      .then(setOpts)
      .catch(() => setOpts(null));
  }, []);

  // Models depend on the chosen brand.
  const models = useMemo(() => {
    if (!opts) return [];
    return sel.brand
      ? opts.models.filter((m) => m.brand_slug === sel.brand)
      : opts.models;
  }, [opts, sel.brand]);

  // Debounced live counter.
  useEffect(() => {
    const id = setTimeout(() => {
      countCars(toQuery(sel))
        .then((r) => setCount(r.count))
        .catch(() => setCount(null));
    }, 300);
    return () => clearTimeout(id);
  }, [sel]);

  function update<K extends keyof Selection>(key: K, value: string) {
    setSel((prev) => {
      const next = { ...prev, [key]: value };
      // Reset model when brand changes and the model no longer belongs to it.
      if (key === "brand") next.model = "";
      return next;
    });
  }

  function submit() {
    const qs = toQueryString(toQuery(sel));
    navigate(`/catalog${qs ? `?${qs}` : ""}`);
  }

  return (
    <section className="quick-pick">
      <h2 className="quick-pick__title">Я ищу:</h2>
      <div className="quick-pick__grid">
        <label className="quick-pick__field">
          <span>Марка</span>
          <select name="brand" value={sel.brand} onChange={(e) => update("brand", e.target.value)}>
            <option value="">Любая</option>
            {opts?.brands.map((b) => (
              <option key={b.slug} value={b.slug}>
                {b.name}
              </option>
            ))}
          </select>
        </label>

        <label className="quick-pick__field">
          <span>Коробка передач</span>
          <select
            name="transmission"
            value={sel.transmission}
            onChange={(e) => update("transmission", e.target.value)}
          >
            <option value="">Любая</option>
            {opts?.transmissions.map((t) => (
              <option key={t.slug} value={t.slug}>
                {t.name}
              </option>
            ))}
          </select>
        </label>

        <label className="quick-pick__field">
          <span>Цена от</span>
          <input
            name="price_min"
            type="number"
            min={0}
            max={PRICE_MAX}
            inputMode="numeric"
            value={sel.price_min}
            onChange={(e) => update("price_min", clampPrice(e.target.value))}
          />
        </label>

        <label className="quick-pick__field">
          <span>Модель</span>
          <select name="model" value={sel.model} onChange={(e) => update("model", e.target.value)}>
            <option value="">Любая</option>
            {models.map((m) => (
              <option key={`${m.brand_slug}/${m.slug}`} value={m.slug}>
                {m.name}
              </option>
            ))}
          </select>
        </label>

        <label className="quick-pick__field">
          <span>Тип двигателя</span>
          <select
            name="engine_type"
            value={sel.engine_type}
            onChange={(e) => update("engine_type", e.target.value)}
          >
            <option value="">Любой</option>
            {opts?.engine_types.map((en) => (
              <option key={en.slug} value={en.slug}>
                {en.name}
              </option>
            ))}
          </select>
        </label>

        <label className="quick-pick__field">
          <span>Цена до</span>
          <input
            name="price_max"
            type="number"
            min={0}
            max={PRICE_MAX}
            inputMode="numeric"
            value={sel.price_max}
            onChange={(e) => update("price_max", clampPrice(e.target.value))}
          />
        </label>

        <label className="quick-pick__field">
          <span>Тип привода</span>
          <select name="drive" value={sel.drive} onChange={(e) => update("drive", e.target.value)}>
            <option value="">Любой</option>
            {opts?.drives.map((d) => (
              <option key={d.slug} value={d.slug}>
                {d.name}
              </option>
            ))}
          </select>
        </label>

        <span className="quick-pick__spacer" aria-hidden="true" />

        <button type="button" className="btn btn--primary quick-pick__submit" onClick={submit}>
          {count === null ? "Показать" : `Найдено ${count} авто`}
        </button>
      </div>
    </section>
  );
}
