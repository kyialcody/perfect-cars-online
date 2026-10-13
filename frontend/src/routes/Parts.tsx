import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, SlidersHorizontal } from "lucide-react";
import { getPartFilters, listParts } from "../api/parts";
import type { PartFiltersResponse, PartListItem } from "../api/parts";
import { parsePartsParams, PARTS_SORT_OPTIONS } from "../lib/partsParams";
import PartCard from "../components/PartCard";
import PartFilters from "../components/parts/PartFilters";
import "./catalog.css";

const PAGE_SIZE = 12;

const FILTER_KEYS = [
  "category",
  "brand",
  "condition",
  "kind",
  "manufacturer",
  "price_min",
  "price_max",
] as const;

type Status = "loading" | "ready" | "error";
type SelectKey = "category" | "condition" | "kind" | "manufacturer";

function getPage(sp: URLSearchParams) {
  const page = Number(sp.get("page"));
  return Number.isFinite(page) && page > 0 ? Math.floor(page) : 1;
}

export default function Parts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useMemo(() => parsePartsParams(searchParams), [searchParams]);
  const currentPage = useMemo(() => getPage(searchParams), [searchParams]);
  const qsKey = searchParams.toString();

  const [opts, setOpts] = useState<PartFiltersResponse | null>(null);
  const [items, setItems] = useState<PartListItem[]>([]);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<Status>("loading");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getPartFilters()
      .then(setOpts)
      .catch(() => setOpts(null));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    const sp = new URLSearchParams(qsKey);
    const base = parsePartsParams(sp);
    listParts({ ...base, page: getPage(sp), page_size: PAGE_SIZE })
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
  }, [qsKey]);

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
    });
  }

  function setParam(key: SelectKey, value: string) {
    patch((sp) => {
      if (value) sp.set(key, value);
      else sp.delete(key);
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
      <h1 className="catalog__title">Запчасти</h1>

      <section className="catalog__top" aria-label="Подбор запчастей">
        <div className="catalog__brands">
          <span className="catalog__section-label">Марки</span>
          <div className="catalog__brand-list">
            {primaryBrand && (
              <button
                type="button"
                className={`catalog__brand-card${params.brand === primaryBrandSlug || !params.brand ? " is-active" : ""}`}
                onClick={() => setBrand(params.brand === primaryBrandSlug ? undefined : primaryBrandSlug)}
              >
                {primaryBrand.logo_url && (
                  <img src={primaryBrand.logo_url} alt="" className="catalog__brand-logo" />
                )}
                <span className="catalog__brand-name">{primaryBrandName}</span>
              </button>
            )}
          </div>
        </div>

        <div className="catalog__quick">
          <div className="catalog__quick-head">
            <div>
              <span className="catalog__section-label">Быстрый подбор запчастей</span>
              <p>{status === "loading" ? "Загрузка…" : `Найдено ${total} запчастей`}</p>
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
            <PartFilters
              opts={opts}
              params={params}
              onParam={setParam}
              onPrice={setPrice}
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
          {status === "loading" ? "Загрузка…" : `Найдено ${total} запчастей`}
        </span>
        <label className="catalog__sort">
          <span>Сортировка</span>
          <select value={params.sort ?? "newest"} onChange={(e) => setSort(e.target.value)}>
            {PARTS_SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {status === "error" && <p>Не удалось загрузить запчасти.</p>}
      {status === "ready" && items.length === 0 && (
        <p className="catalog__empty">Запчасти не найдены. Попробуйте изменить фильтры.</p>
      )}

      <div className="catalog__grid">
        {items.map((part) => (
          <PartCard key={part.id} part={part} />
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
