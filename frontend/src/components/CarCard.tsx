import { Link, useLocation } from "react-router-dom";
import { Zap, BatteryCharging, Fuel, Timer, Gauge } from "lucide-react";
import type { CarListItem } from "../api/types";
import { useLeads } from "./leads/LeadContext";
import { formatPrice, formatNumber } from "../lib/format";
import "./car-card.css";

// Reusable catalog card (design: docs/design/home-top.png, car-card-desktop.png).
// «Купить» opens the lead modal — implemented in #17; here it is a placeholder.
export default function CarCard({ car }: { car: CarListItem }) {
  const location = useLocation();
  const { submitLead } = useLeads();
  const sourceCondition =
    new URLSearchParams(location.search).get("condition") === "used"
      ? "used"
      : car.condition;

  // Спецпредложения отображаются той же карточкой, что и авто с пробегом
  // (год в заголовке, сетка характеристик «значение: метка», галерея).
  const isUsed = car.condition === "used" || car.condition === "special";

  // New cars show performance icons; used cars show a label:value spec grid
  // (power / engine volume / drive / body / transmission / mileage) per the
  // «Авто с пробегом» reference.
  const specs = [
    car.power_hp != null && { icon: Zap, label: `${car.power_hp} л.с.` },
    car.fuel_consumption != null && {
      icon: BatteryCharging,
      label: `${formatNumber(car.fuel_consumption)} кВт·ч`,
    },
    car.fuel_consumption_petrol != null && {
      icon: Fuel,
      label: `${formatNumber(car.fuel_consumption_petrol)} л/100 км`,
    },
    car.acceleration_0_100 != null && {
      icon: Timer,
      label: `${formatNumber(car.acceleration_0_100)} с`,
    },
    car.max_speed != null && { icon: Gauge, label: `${car.max_speed} км/ч` },
  ].filter(Boolean) as { icon: typeof Zap; label: string }[];

  const usedSpecs = [
    car.power_hp != null && { label: "Мощность", value: `${car.power_hp} л.с.` },
    car.engine_volume != null && {
      label: "Объем двигателя",
      value: `${formatNumber(car.engine_volume)} л`,
    },
    car.drive && { label: "Привод", value: car.drive },
    car.body_type && { label: "Кузов", value: car.body_type },
    car.transmission && { label: "КПП", value: car.transmission },
    car.mileage != null && { label: "Пробег", value: `${formatNumber(car.mileage)} км` },
  ].filter(Boolean) as { label: string; value: string }[];

  // Used cars include the year in the title, e.g. «Toyota Camry 2013».
  const title = isUsed && car.year ? `${car.title} ${car.year}` : car.title;

  return (
    <article className={`car-card${isUsed ? " car-card--used" : ""}`}>
      <div className="car-card__media">
        {car.benefit_badge && <span className="car-card__badge">{car.benefit_badge}</span>}
        {car.image_url ? (
          <img src={car.image_url} alt={title} loading="lazy" />
        ) : (
          <div className="car-card__media-empty" aria-hidden="true" />
        )}
      </div>

      <div className="car-card__body">
        <h3 className="car-card__title">{title}</h3>
        {!isUsed && <p className="car-card__status">{car.status_text ?? "\u00a0"}</p>}

        {isUsed ? (
          <dl className="car-card__used-specs">
            {usedSpecs.map(({ label, value }) => (
              <div key={label}>
                <dt>{label}:</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <ul className="car-card__specs" aria-hidden={specs.length === 0}>
            {specs.map(({ icon: Icon, label }) => (
              <li key={label}>
                <Icon size={16} aria-hidden="true" />
                {label}
              </li>
            ))}
          </ul>
        )}

        <div className="car-card__price">
          <span className="car-card__price-new">
            <span className="car-card__price-prefix">от</span> {formatPrice(car.price)}
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
                  source_title: `Купить ${title}`,
                  dedupe_key: `purchase:${car.id}`,
                  car_id: car.id,
                  comment: `Заявка с кнопки «Купить» в каталоге: ${title}`,
                },
                { confirm: true },
              )
            }
          >
            Купить
          </button>
          <Link
            to={`/car/${car.slug}`}
            state={{ catalogCondition: sourceCondition }}
            className="car-card__more"
          >
            Подробнее
          </Link>
        </div>
      </div>
    </article>
  );
}
