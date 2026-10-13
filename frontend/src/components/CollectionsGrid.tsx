import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getCollections } from "../api/home";
import type { HomeCollection } from "../api/types";
import "./collections-grid.css";

const PAGE_SIZE = 9; // 3 × 3 grid per page

function collectionHref(item: HomeCollection): string {
  return item.button_url ?? (item.car ? `/car/${item.car.slug}` : "/catalog");
}

export default function CollectionsGrid() {
  const [items, setItems] = useState<HomeCollection[]>([]);
  const [page, setPage] = useState(0);

  useEffect(() => {
    getCollections()
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  if (items.length === 0) return null;

  const pages = Math.ceil(items.length / PAGE_SIZE);
  const start = page * PAGE_SIZE;
  const visible = items.slice(start, start + PAGE_SIZE);

  return (
    <section className="picks" aria-label="Наши подборки">
      <div className="picks__head">
        <h2 className="picks__title">Наши подборки</h2>
        {pages > 1 && (
          <div className="picks__nav">
            <button
              type="button"
              aria-label="Предыдущие подборки"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft size={20} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Следующие подборки"
              onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
              disabled={page >= pages - 1}
            >
              <ChevronRight size={20} aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      <div className="picks__grid">
        {visible.map((item) => (
          <Link className="pick" key={item.id} to={collectionHref(item)}>
            {item.image_url || item.car?.image_url ? (
              <img
                className="pick__img"
                src={item.image_url ?? item.car?.image_url ?? ""}
                alt=""
                loading="lazy"
              />
            ) : (
              <span className="pick__placeholder">Zeekr</span>
            )}
            <span className="pick__overlay">
              <span className="pick__name">{item.title}</span>
              <span className="pick__cta">{item.button_text ?? "Посмотреть"}</span>
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
