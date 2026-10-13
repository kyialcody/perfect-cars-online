import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, X } from "lucide-react";
import { listCars } from "../api/catalog";
import type { CarListItem } from "../api/types";
import CarCard from "../components/CarCard";
import "./search.css";

const DEBOUNCE_MS = 300;
const PAGE_SIZE = 24;

// Full-screen car search opened from the mobile header. Matches by brand/model
// text (backend `q` param); results reuse the standard catalog card.
export default function Search() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(() => searchParams.get("q") ?? "");
  const [items, setItems] = useState<CarListItem[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus the field on open so the user can type immediately.
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Debounced fetch on query change; an empty query shows the idle empty state.
  useEffect(() => {
    const trimmed = query.trim();
    // Keep the URL shareable/back-friendly without spamming history.
    setSearchParams(trimmed ? { q: trimmed } : {}, { replace: true });

    if (!trimmed) {
      setItems([]);
      setStatus("idle");
      return;
    }

    setStatus("loading");
    let cancelled = false;
    const timer = setTimeout(() => {
      listCars({ q: trimmed, page: 1, page_size: PAGE_SIZE, sort: "newest" })
        .then((res) => {
          if (cancelled) return;
          setItems(res.items);
          setStatus("ready");
        })
        .catch(() => {
          if (cancelled) return;
          setItems([]);
          setStatus("error");
        });
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, setSearchParams]);

  return (
    <div className="search-page">
      <div className="container search-page__bar">
        <button
          type="button"
          className="search-page__back"
          aria-label="Назад"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft size={22} aria-hidden="true" />
        </button>
        <div className="search-page__field">
          <input
            ref={inputRef}
            type="search"
            className="search-page__input"
            placeholder="Поиск автомобилей"
            aria-label="Поиск автомобилей"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {query && (
            <button
              type="button"
              className="search-page__clear"
              aria-label="Очистить"
              onClick={() => {
                setQuery("");
                inputRef.current?.focus();
              }}
            >
              <X size={18} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className="container search-page__results">
        {status === "error" && <p className="search-page__hint">Не удалось выполнить поиск.</p>}
        {status === "ready" && items.length === 0 && (
          <p className="search-page__hint">Ничего не найдено. Попробуйте другой запрос.</p>
        )}
        <div className="search-page__grid">
          {items.map((car) => (
            <CarCard key={car.id} car={car} />
          ))}
        </div>
      </div>
    </div>
  );
}
