import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, SlidersHorizontal } from "lucide-react";
import { getFilters, listCars } from "../api/catalog";
import type { CarListItem, FiltersResponse } from "../api/types";
import { parseCatalogParams, SORT_OPTIONS } from "../lib/catalogParams";
import CarCard from "../components/CarCard";
import CatalogFilters from "../components/catalog/CatalogFilters";
import "./catalog.css";

const PAGE_SIZE = 12;

// Keys that count as an "active" filter. Sort/page are presentation, not filters.
const FILTER_KEYS = [
  "brand",
  "model",
  "body_type",
  "transmission",
  "drive",
  "engine_type",
  "condition",
  "year_min",
  "year_max",
  "price_min",
  "price_max",
  "mileage_max",
] as const;

type Status = "loading" | "ready" | "error";

function getPage(sp: URLSearchParams) {
  const page = Number(sp.get("page"));
  return Number.isFinite(page) && page > 0 ? Math.floor(page) : 1;
}

export default function Catalog({
  usedOnly = false,
  specialOnly = false,
}: {
  usedOnly?: boolean;
  specialOnly?: boolean;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  // The dedicated «Авто с пробегом» / «Спецпредложения» routes lock the
  // condition (used / special) — the «Спецпредложения» screen mirrors the used
  // one in everything but the locked condition and title.
  const lockedCondition: "used" | "special" | null = usedOnly
    ? "used"
    : specialOnly
      ? "special"
      : null;
  const params = useMemo(() => {
    const parsed = parseCatalogParams(searchParams);
    return lockedCondition ? { ...parsed, condition: lockedCondition } : parsed;
  }, [searchParams, lockedCondition]);
  const currentPage = useMemo(() => getPage(searchParams), [searchParams]);
  const qsKey = searchParams.toString();

  const [opts, setOpts] = useState<FiltersResponse | null>(null);
  const [items, setItems] = useState<CarListItem[]>([]);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<Status>("loading");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getFilters()
      .then(setOpts)
      .catch(() => setOpts(null));
  }, []);

  // Query changed → load exactly that catalog page. Parsing fresh from qsKey keeps
  // the dependency list honest (params is derived from the same string).
  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    const sp = new URLSearchParams(qsKey);
    const base = parseCatalogParams(sp);
    if (lockedCondition) base.condition = lockedCondition;
    listCars({ ...base, page: getPage(sp), page_size: PAGE_SIZE })
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
        setTotal(res.total);
        setPages(res.pages);
        setStatus("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setItems([]);
        setTotal(0);
        setPages(1);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [qsKey, lockedCondition]);

  // All filter writes go through the URL, so the view is always shareable.
  function patch(mutate: (sp: URLSearchParams) => void, keepPage = false) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      mutate(next);
      if (!keepPage) next.delete("page");
      return next;
    });
  }

  function setBrand(slug: string | undefined) {
    patch((sp) => {
      if (slug) sp.set("brand", slug);
      else sp.delete("brand");
      sp.delete("model"); // a model belongs to a brand
    });
  }

  function setParam(
    key: (typeof FILTER_KEYS)[number] | "model",
    value: string,
  ) {
    patch((sp) => {
      if (value) sp.set(key, value);
      else sp.delete(key);
      // Used-only fields are meaningless for new cars — drop them.
      if (key === "condition" && value !== "used") {
        sp.delete("year_min");
        sp.delete("year_max");
        sp.delete("mileage_max");
      }
    });
  }

  function setPrice(min: number | undefined, max: number | undefined) {
    patch((sp) => {
      if (min != null) sp.set("price_min", String(min));
      else sp.delete("price_min");
      if (max != null) sp.set("price_max", String(max));
      else sp.delete("price_max");
    });
  }

  function setSort(value: string) {
    patch((sp) => {
      if (value && value !== "newest") sp.set("sort", value);
      else sp.delete("sort");
    });
  }

  function reset() {
    setSearchParams(new URLSearchParams());
  }

  function setPage(nextPage: number) {
    patch((sp) => {
      if (nextPage > 1) sp.set("page", String(nextPage));
      else sp.delete("page");
    }, true);
  }

  const hasActiveFilters = FILTER_KEYS.some((k) => searchParams.has(k));
  const primaryBrand = opts?.brands.find((brand) => brand.slug === "zeekr") ?? opts?.brands[0];
  const primaryBrandSlug = primaryBrand?.slug ?? "zeekr";
  const primaryBrandName = primaryBrand?.name ?? "Zeekr";
  const canGoPrev = currentPage > 1 && status === "ready";
  const canGoNext = currentPage < pages && status === "ready";

  return (
    <div className="container catalog">
      <h1 className="catalog__title">
        {usedOnly ? "Авто с пробегом" : specialOnly ? "Спецпредложения" : "Каталог авто"}
      </h1>

      <section className="catalog__top" aria-label="Подбор авто">
        <div className="catalog__brands">
          <span className="catalog__section-label">Марки</span>
          <div className="catalog__brand-list">
            <button
              type="button"
              className={`catalog__brand-card${params.brand === primaryBrandSlug || !params.brand ? " is-active" : ""}`}
              onClick={() => setBrand(params.brand === primaryBrandSlug ? undefined : primaryBrandSlug)}
            >
              {primaryBrand?.logo_url && (
                <img src={primaryBrand.logo_url} alt="" className="catalog__brand-logo" />
              )}
              <span className="catalog__brand-name">{primaryBrandName}</span>
            </button>
          </div>
        </div>

        <div className="catalog__quick">
          <div className="catalog__quick-head">
            <div>
              <span className="catalog__section-label">Быстрый подбор авто</span>
              <p>{status === "loading" ? "Загрузка…" : `Найдено ${total} авто`}</p>
            </div>
            <button
              type="button"
              className="btn btn--outline catalog__filters-toggle"
              onClick={() => setFiltersOpen((v) => !v)}
              aria-expanded={filtersOpen}
            >
              <SlidersHorizontal size={16} aria-hidden="true" />
              Фильтры
              {hasActiveFilters && <span className="catalog__filters-dot" aria-hidden="true" />}
            </button>
          </div>

          <div className={`catalog__filters-panel${filtersOpen ? " is-open" : ""}`}>
            <CatalogFilters
              opts={opts}
              params={params}
              onParam={setParam}
              onPrice={setPrice}
              onReset={reset}
              hasActiveFilters={hasActiveFilters}
              lockCondition={lockedCondition != null}
              simple={lockedCondition != null}
              onShow={() => {
                setFiltersOpen(false);
                resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
            />
          </div>
        </div>
      </section>

      <div className="catalog__toolbar" ref={resultsRef}>
        <span className="catalog__count">
          {status === "loading" ? "Загрузка…" : `Найдено ${total} авто`}
        </span>
        <label className="catalog__sort">
          <span>Сортировка</span>
          <select value={params.sort ?? "newest"} onChange={(e) => setSort(e.target.value)}>
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {status === "error" && <p>Не удалось загрузить каталог.</p>}
      {status === "ready" && items.length === 0 && (
        <p className="catalog__empty">Автомобили не найдены. Попробуйте изменить фильтры.</p>
      )}

      <div className="catalog__grid">
        {items.map((car) => (
          <CarCard key={car.id} car={car} />
        ))}
      </div>

      {pages > 1 && (
        <div className="catalog__pagination" aria-label="Страницы каталога">
          <button
            type="button"
            className="catalog__page-arrow"
            onClick={() => setPage(currentPage - 1)}
            disabled={!canGoPrev}
            aria-label="Предыдущая страница"
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="catalog__page-arrow"
            onClick={() => setPage(currentPage + 1)}
            disabled={!canGoNext}
            aria-label="Следующая страница"
          >
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  );
}
