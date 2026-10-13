import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BatteryCharging, Fuel, Gift, Gauge, Timer, Zap } from "lucide-react";
import { getCar } from "../api/catalog";
import type { CarDetail, FeatureGroup } from "../api/types";
import CarCard from "../components/CarCard";
import Gallery from "../components/catalog/Gallery";
import { useBreadcrumbTitle } from "../components/layout/BreadcrumbTitleContext";
import { useLeads } from "../components/leads/LeadContext";
import { formatNumber, formatPrice } from "../lib/format";
import "./car-page.css";

const FEATURE_TITLES: Record<string, string> = {
  safety: "Безопасность",
  exterior: "Экстерьер",
  interior: "Интерьер",
};

function FeatureGroups({ groups }: { groups: FeatureGroup[] }) {
  return (
    <div className="car-detail__features">
      {groups.map((group) => (
        <section key={group.block}>
          <h3>{FEATURE_TITLES[group.block] ?? group.block}</h3>
          <ul>
            {group.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export default function CarPage() {
  const { slug } = useParams();
  const [car, setCar] = useState<CarDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const { setTitle } = useBreadcrumbTitle();
  const { submitLead } = useLeads();

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setStatus("loading");
    getCar(slug)
      .then((data) => {
        if (cancelled) return;
        setCar(data);
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // Feed the loaded car's title to the breadcrumb, and clear it on leave so the
  // next page doesn't briefly show the wrong name.
  useEffect(() => {
    setTitle(car?.title ?? null);
    return () => setTitle(null);
  }, [car, setTitle]);

  const mainImage = useMemo(() => car?.images.find((img) => img.is_main) ?? car?.images[0], [car]);

  // The hero banner is the active colour's picture (1 colour = 1 banner). Start
  // on the first colour that actually has a banner.
  const [activeColor, setActiveColor] = useState(0);
  useEffect(() => {
    if (!car) return;
    const idx = car.colors.findIndex((c) => c.image_url);
    setActiveColor(idx >= 0 ? idx : 0);
  }, [car]);
  const bannerImage = car?.colors[activeColor]?.image_url ?? null;

  if (status === "loading") {
    return <div className="container car-detail car-detail--state">Загрузка карточки авто…</div>;
  }

  if (status === "error" || !car) {
    return (
      <div className="container car-detail car-detail--state">
        <h1>Карточка не найдена</h1>
        <Link to="/catalog" className="btn btn--primary">
          Вернуться в каталог
        </Link>
      </div>
    );
  }

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

  // Used cars: a single specific vehicle, so the detail shows car-level specs
  // and a booking block instead of the new-car «Комплектации» table.
  // Спецпредложения используют тот же макет, что и авто с пробегом.
  const isUsed = car.condition === "used" || car.condition === "special";
  const detailTitle = isUsed && car.year ? `${car.title} ${car.year}` : car.title;
  const usedChips = [
    car.engine_volume != null && `${formatNumber(car.engine_volume)} л`,
    car.power_hp != null && `${car.power_hp} л.с.`,
    car.transmission,
    car.drive,
  ].filter(Boolean) as string[];
  const usedSpecRows = [
    car.drive && { label: "Привод", value: car.drive },
    car.body_type && { label: "Кузов", value: car.body_type },
    car.year != null && { label: "Год", value: String(car.year) },
    car.mileage != null && { label: "Пробег", value: `${formatNumber(car.mileage)} км` },
  ].filter(Boolean) as { label: string; value: string }[];

  if (isUsed) {
    return (
      <div className="container car-detail car-detail--used-page">
        <h1 className="car-detail__sr-title">{detailTitle}</h1>
        <section className="car-detail__used-layout" aria-label={detailTitle}>
          <Gallery images={car.images} title={detailTitle} heading={null} variant="used" />
          <aside className="car-detail__used-panel">
            <h2>{detailTitle}</h2>
            {usedChips.length > 0 && (
              <ul className="car-detail__used-chips">
                {usedChips.map((chip) => (
                  <li key={chip}>{chip}</li>
                ))}
              </ul>
            )}
            <strong className="car-detail__used-main-price">{formatPrice(car.price)}</strong>
            <button
              type="button"
              className="car-detail__used-book"
              onClick={() =>
                submitLead(
                  {
                    source: "car_detail",
                    source_title: `Забронировать ${detailTitle}`,
                    dedupe_key: `book:${car.id}`,
                    car_id: car.id,
                    comment: `Заявка на бронь автомобиля: ${detailTitle}`,
                  },
                  { confirm: true },
                )
              }
            >
              Забронировать
            </button>
            {car.benefits.length > 0 && (
              <ul className="car-detail__used-benefits">
                {car.benefits.slice(0, 3).map((benefit) => (
                  <li key={benefit.text}>
                    <Gift size={16} aria-hidden="true" />
                    {benefit.text}
                  </li>
                ))}
              </ul>
            )}
            {usedSpecRows.length > 0 && (
              <dl className="car-detail__used-specs">
                {usedSpecRows.map((row) => (
                  <div key={row.label}>
                    <dt>{row.label}:</dt>
                    <dd>{row.value}</dd>
                  </div>
                ))}
              </dl>
            )}
            {car.status_text && <p className="car-detail__used-status">{car.status_text}</p>}
          </aside>
        </section>

        {car.similar.length > 0 && (
          <section className="car-detail__similar">
            <h2>Похожие предложения</h2>
            <div className="car-detail__similar-grid">
              {car.similar.map((item) => (
                <CarCard key={item.id} car={item} />
              ))}
            </div>
          </section>
        )}
      </div>
    );
  }

  return (
    <div className="container car-detail">
      <section className="car-detail__hero">
        <h1 className="car-detail__sr-title">{detailTitle}</h1>
        {bannerImage ? (
          <img className="car-detail__hero-bg" src={bannerImage} alt={detailTitle} />
        ) : (
          <div className="car-detail__hero-empty">{detailTitle}</div>
        )}

        {car.colors.length > 0 && (
          <div className="car-detail__colors" aria-label="Цвета">
            <span>Цвета</span>
            {car.colors[activeColor]?.name && (
              <span className="car-detail__color-name">Цвет: {car.colors[activeColor].name}</span>
            )}
            <div>
              {car.colors.map((color, index) => (
                <button
                  type="button"
                  key={color.name}
                  className={index === activeColor ? "is-active" : ""}
                  title={color.name}
                  aria-label={color.name}
                  aria-pressed={index === activeColor}
                  style={{ background: color.hex }}
                  onClick={() => setActiveColor(index)}
                />
              ))}
            </div>
          </div>
        )}
      </section>

      <Gallery
        images={car.images}
        title={detailTitle}
        heading={`Автомобили ${detailTitle} в наличии`}
      />

      <section className="car-detail__trims" aria-label="Комплектации">
        <div className="car-detail__trim-head" aria-hidden="true">
          <span>Комплектация</span>
          <span>Двигатель</span>
          <span>Коробка передач</span>
          <span>Привод</span>
          <span>Цена</span>
          <span>Со скидкой</span>
        </div>
        {car.trims.length > 0 ? (
          car.trims.map((trim) => (
            <article key={trim.id} className="car-trim">
              <div className="car-trim__summary">
                <strong>{trim.name}</strong>
                <span>
                  {trim.engine_volume ? `${formatNumber(trim.engine_volume)} л · ` : ""}
                  {trim.power_hp ? `${trim.power_hp} л.с.` : "—"}
                </span>
                <span>{trim.transmission ?? "—"}</span>
                <span>{trim.drive ?? "—"}</span>
                <span>{formatPrice(trim.price)}</span>
                <strong>{formatPrice(trim.price_discount ?? trim.price)}</strong>
              </div>
              <div className="car-trim__body">
                <div className="car-trim__image">
                  {trim.image_url ? (
                    <img src={trim.image_url} alt={trim.name} />
                  ) : mainImage ? (
                    <img src={mainImage.url} alt="" />
                  ) : (
                    <span>{car.title}</span>
                  )}
                </div>
                <div>
                  <h3>{car.title}</h3>
                  {car.status_text && <p>{car.status_text}</p>}
                  <span>Доступна в {Math.max(car.colors.length, 1)} цветах</span>
                </div>
                <ul className="car-trim__mini-specs">
                  {specs.map(({ icon: Icon, label }) => (
                    <li key={label}>
                      <Icon size={14} aria-hidden="true" />
                      {label}
                    </li>
                  ))}
                </ul>
                <ul className="car-trim__gifts">
                  {car.gifts.map((gift) => (
                    <li key={gift}>
                      <Gift size={16} aria-hidden="true" />
                      {gift}
                    </li>
                  ))}
                </ul>
                <div className="car-trim__price">
                  <strong>{formatPrice(trim.price_discount ?? trim.price)}</strong>
                  {trim.price_discount && <span>{formatPrice(trim.price)}</span>}
                  <button
                    type="button"
                    onClick={() =>
                      submitLead(
                        {
                          source: "car_detail",
                          source_title: `Забронировать ${car.title} ${trim.name}`,
                          dedupe_key: `book:${car.id}:trim:${trim.id}`,
                          car_id: car.id,
                          comment: `Комплектация: ${trim.name}. Цена: ${formatPrice(trim.price_discount ?? trim.price)}`,
                        },
                        { confirm: true },
                      )
                    }
                  >
                    Забронировать
                  </button>
                </div>
              </div>
            </article>
          ))
        ) : (
          <div className="car-detail__empty-block">Комплектации скоро появятся</div>
        )}
        {car.features.length > 0 && <FeatureGroups groups={car.features} />}
      </section>
      

      {car.similar.length > 0 && (
        <section className="car-detail__similar">
          <h2>Похожие предложения</h2>
          <div className="car-detail__similar-grid">
            {car.similar.map((item) => (
              <CarCard key={item.id} car={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
