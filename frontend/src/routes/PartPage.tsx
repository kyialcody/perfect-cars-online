import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getPart } from "../api/parts";
import type { PartDetail } from "../api/parts";
import type { ImageOut } from "../api/types";
import PartCard from "../components/PartCard";
import Gallery from "../components/catalog/Gallery";
import { useBreadcrumbTitle } from "../components/layout/BreadcrumbTitleContext";
import { useLeads } from "../components/leads/LeadContext";
import { formatPrice } from "../lib/format";
import { PART_CONDITION_LABEL, PART_KIND_LABEL } from "../lib/partsParams";
import "./car-page.css";

export default function PartPage() {
  const { slug } = useParams();
  const [part, setPart] = useState<PartDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const { setTitle } = useBreadcrumbTitle();
  const { submitLead } = useLeads();

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setStatus("loading");
    getPart(slug)
      .then((data) => {
        if (cancelled) return;
        setPart(data);
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    setTitle(part?.name ?? null);
    return () => setTitle(null);
  }, [part, setTitle]);

  // The part gallery has string|null image urls; drop the empty ones for the
  // shared Gallery, which expects concrete ImageOut.
  const galleryImages = useMemo<ImageOut[]>(
    () =>
      (part?.images ?? [])
        .filter((img): img is ImageOut & { url: string } => Boolean(img.url))
        .map((img) => ({ url: img.url, is_main: img.is_main, sort_order: img.sort_order })),
    [part],
  );

  if (status === "loading") {
    return <div className="container car-detail car-detail--state">Загрузка карточки запчасти…</div>;
  }

  if (status === "error" || !part) {
    return (
      <div className="container car-detail car-detail--state">
        <h1>Запчасть не найдена</h1>
        <Link to="/parts" className="btn btn--primary">
          Вернуться к запчастям
        </Link>
      </div>
    );
  }

  const chips = [
    part.category,
    PART_KIND_LABEL[part.kind],
    PART_CONDITION_LABEL[part.condition],
  ].filter(Boolean) as string[];

  const specRows = [
    part.brand && { label: "Марка", value: part.brand },
    part.manufacturer && { label: "Производитель", value: part.manufacturer },
    part.part_number && { label: "Артикул", value: part.part_number },
    part.category && { label: "Категория", value: part.category },
  ].filter(Boolean) as { label: string; value: string }[];

  return (
    <div className="container car-detail car-detail--used-page">
      <h1 className="car-detail__sr-title">{part.name}</h1>
      <section className="car-detail__used-layout" aria-label={part.name}>
        <Gallery images={galleryImages} title={part.name} heading={null} variant="used" />
        <aside className="car-detail__used-panel">
          <h2>{part.name}</h2>
          {chips.length > 0 && (
            <ul className="car-detail__used-chips">
              {chips.map((chip) => (
                <li key={chip}>{chip}</li>
              ))}
            </ul>
          )}
          <strong className="car-detail__used-main-price">{formatPrice(part.price)}</strong>
          <button
            type="button"
            className="car-detail__used-book"
            onClick={() =>
              submitLead(
                {
                  source: "car_detail",
                  source_title: `Купить запчасть: ${part.name}`,
                  dedupe_key: `part-purchase:${part.id}`,
                  comment: `Заявка на запчасть: ${part.name}`,
                },
                { confirm: true },
              )
            }
          >
            Купить
          </button>
          {specRows.length > 0 && (
            <dl className="car-detail__used-specs">
              {specRows.map((row) => (
                <div key={row.label}>
                  <dt>{row.label}:</dt>
                  <dd>{row.value}</dd>
                </div>
              ))}
            </dl>
          )}
          {part.status_text && <p className="car-detail__used-status">{part.status_text}</p>}
        </aside>
      </section>

      {part.description && (
        <section className="car-detail__similar" aria-label="Описание">
          <h2>Описание</h2>
          <p>{part.description}</p>
        </section>
      )}

      {part.similar.length > 0 && (
        <section className="car-detail__similar">
          <h2>Похожие предложения</h2>
          <div className="car-detail__similar-grid">
            {part.similar.map((item) => (
              <PartCard key={item.id} part={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
