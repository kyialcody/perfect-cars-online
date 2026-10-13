import { Link } from "react-router-dom";
import type { PartListItem } from "../api/parts";
import { useLeads } from "./leads/LeadContext";
import { formatPrice } from "../lib/format";
import { PART_CONDITION_LABEL, PART_KIND_LABEL } from "../lib/partsParams";
import "./car-card.css";

// Part catalog card. Structurally mirrors the used-car card (spec grid,
// «Купить» → lead, «Подробнее» → detail) and reuses car-card.css.
export default function PartCard({ part }: { part: PartListItem }) {
  const { submitLead } = useLeads();

  const specs = [
    part.category && { label: "Категория", value: part.category },
    part.brand && { label: "Марка", value: part.brand },
    part.manufacturer && { label: "Производитель", value: part.manufacturer },
    part.part_number && { label: "Артикул", value: part.part_number },
    { label: "Состояние", value: PART_CONDITION_LABEL[part.condition] },
    { label: "Тип", value: PART_KIND_LABEL[part.kind] },
  ].filter(Boolean) as { label: string; value: string }[];

  return (
    <article className="car-card car-card--used">
      <div className="car-card__media">
        {part.benefit_badge && <span className="car-card__badge">{part.benefit_badge}</span>}
        {part.image_url ? (
          <img src={part.image_url} alt={part.name} loading="lazy" />
        ) : (
          <div className="car-card__media-empty" aria-hidden="true" />
        )}
      </div>

      <div className="car-card__body">
        <h3 className="car-card__title">{part.name}</h3>

        <dl className="car-card__used-specs">
          {specs.map(({ label, value }) => (
            <div key={label}>
              <dt>{label}:</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>

        <div className="car-card__price">
          <span className="car-card__price-new">
            <span className="car-card__price-prefix">от</span> {formatPrice(part.price)}
          </span>
        </div>

        <div className="car-card__actions">
          <button
            type="button"
            className="car-card__buy"
            onClick={() =>
              submitLead(
                {
                  source: "catalog",
                  source_title: `Купить запчасть: ${part.name}`,
                  dedupe_key: `part-purchase:${part.id}`,
                  comment: `Заявка на запчасть из каталога: ${part.name}`,
                },
                { confirm: true },
              )
            }
          >
            Купить
          </button>
          <Link to={`/part/${part.slug}`} className="car-card__more">
            Подробнее
          </Link>
        </div>
      </div>
    </article>
  );
}
