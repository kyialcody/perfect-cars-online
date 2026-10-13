import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Clock, MapPin, Phone } from "lucide-react";
import { getFilters } from "../api/catalog";
import { listCars } from "../api/catalog";
import { getHomeContent, getLocations } from "../api/home";
import type {
  CarListItem,
  DealerLocation,
  FiltersResponse,
  HomeAbout as HomeAboutData,
  HomeCollection,
  HomePromo,
} from "../api/types";
import BrandSidebar from "../components/catalog/BrandSidebar";
import CarCard from "../components/CarCard";
import HomeAbout from "../components/HomeAbout";
import PromoOffer from "../components/PromoOffer";
import QuickPick from "../components/QuickPick";
import YandexMap from "../components/YandexMap";
import "./home.css";

const PAGE_SIZE = 6;

function fallbackPromo(): HomePromo {
  return {
    id: 0,
    image_url: null,
    link_url: "/catalog?brand=zeekr",
  };
}

export default function Home() {
  const [homePromos, setHomePromos] = useState<HomePromo[]>([]);
  const [collections, setCollections] = useState<HomeCollection[]>([]);
  const [about, setAbout] = useState<HomeAboutData | null>(null);
  const [locations, setLocations] = useState<DealerLocation[]>([]);
  const [mapFailed, setMapFailed] = useState(false);
  const [filters, setFilters] = useState<FiltersResponse | null>(null);
  const [selectedBrand, setSelectedBrand] = useState<string | undefined>("zeekr");
  const [cars, setCars] = useState<CarListItem[]>([]);
  const [visible, setVisible] = useState(PAGE_SIZE);
  const [total, setTotal] = useState(0);
  const [slide, setSlide] = useState(0);

  useEffect(() => {
    getHomeContent()
      .then((data) => {
        setHomePromos(data.promos);
        setCollections(data.collections);
        setAbout(data.about);
        setSlide(0);
      })
      .catch(() => {
        setHomePromos([]);
        setCollections([]);
        setAbout(null);
      });

    getLocations()
      .then(setLocations)
      .catch(() => setLocations([]));

    getFilters()
      .then((data) => {
        setFilters(data);
        if (!data.brands.some((brand) => brand.slug === "zeekr")) {
          setSelectedBrand(data.brands[0]?.slug);
        }
      })
      .catch(() => setFilters(null));
  }, []);

  useEffect(() => {
    listCars({
      brand: selectedBrand,
      page: 1,
      page_size: visible,
      sort: "newest",
    })
      .then((data) => {
        setCars(data.items);
        setTotal(data.total);
      })
      .catch(() => {
        setCars([]);
        setTotal(0);
      });
  }, [selectedBrand, visible]);

  const slides = useMemo<HomePromo[]>(
    () => (homePromos.length > 0 ? homePromos : [fallbackPromo()]),
    [homePromos],
  );
  const current = Math.min(slide, slides.length - 1);
  const promo = slides[current];
  const goTo = (index: number) => setSlide((index + slides.length) % slides.length);
  const brands = useMemo(() => filters?.brands ?? [], [filters]);

  const collectionsTrack = useRef<HTMLDivElement>(null);
  const scrollCollections = (direction: 1 | -1) => {
    const track = collectionsTrack.current;
    if (!track) return;
    track.scrollBy({ left: direction * track.clientWidth * 0.8, behavior: "smooth" });
  };

  return (
    <div className="home-page">
      <section className="container home-hero" aria-label="Промо Zeekr">
        {(() => {
          const inner = promo.image_url ? (
            <img className="home-hero__image" src={promo.image_url} alt="" />
          ) : (
            <div className="home-hero__zeekr" aria-hidden="true">
              <span>Zeekr</span>
            </div>
          );
          if (!promo.link_url) {
            return <div className="home-hero__banner">{inner}</div>;
          }
          return promo.link_url.startsWith("http") ? (
            <a className="home-hero__banner" href={promo.link_url}>
              {inner}
            </a>
          ) : (
            <Link className="home-hero__banner" to={promo.link_url}>
              {inner}
            </Link>
          );
        })()}
        {slides.length > 1 && (
          <>
            <button
              type="button"
              className="home-hero__arrow home-hero__arrow--prev"
              aria-label="Предыдущий баннер"
              onClick={() => goTo(current - 1)}
            >
              <ChevronLeft size={28} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="home-hero__arrow home-hero__arrow--next"
              aria-label="Следующий баннер"
              onClick={() => goTo(current + 1)}
            >
              <ChevronRight size={28} aria-hidden="true" />
            </button>
            <div className="home-hero__dots" role="tablist" aria-label="Баннеры">
              {slides.map((item, index) => (
                <button
                  type="button"
                  key={item.id}
                  className={index === current ? "is-active" : ""}
                  role="tab"
                  aria-selected={index === current}
                  aria-label={`Баннер ${index + 1}`}
                  onClick={() => goTo(index)}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <section className="container home-body" aria-label="Подбор Zeekr">
        <aside className="home-body__brands">
          <BrandSidebar
            brands={brands}
            selected={selectedBrand}
            onSelect={(slug) => {
              setSelectedBrand(slug);
              setVisible(PAGE_SIZE);
            }}
          />
        </aside>

        <div className="home-body__main">
          <QuickPick />

          <div className="home-stock">
            <div className="home-section-head">
              <h2>Автомобили в наличии</h2>
            </div>
            <div className="home-stock__grid">
              {cars.map((car) => (
                <CarCard key={car.id} car={car} />
              ))}
            </div>
            {visible < total && (
              <button
                type="button"
                className="btn btn--primary home-stock__more"
                onClick={() => setVisible((value) => value + PAGE_SIZE)}
              >
                Показать ещё
              </button>
            )}
          </div>

          {collections.length > 0 && (
            <div className="home-collections">
              <div className="home-section-head home-section-head--carousel">
                <h2>Наши подборки</h2>
                {collections.length > 1 && (
                  <div className="home-collections__nav">
                    <button
                      type="button"
                      aria-label="Предыдущие подборки"
                      onClick={() => scrollCollections(-1)}
                    >
                      <ChevronLeft size={20} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      aria-label="Следующие подборки"
                      onClick={() => scrollCollections(1)}
                    >
                      <ChevronRight size={20} aria-hidden="true" />
                    </button>
                  </div>
                )}
              </div>
              <div className="home-collections__track" ref={collectionsTrack}>
                {collections.map((item) => (
                  <Link
                    className="home-collection"
                    key={item.id}
                    to={item.button_url ?? (item.car ? `/car/${item.car.slug}` : "/catalog")}
                  >
                    {item.image_url || item.car?.image_url ? (
                      <img
                        className="home-collection__img"
                        src={item.image_url ?? item.car?.image_url ?? ""}
                        alt=""
                        loading="lazy"
                      />
                    ) : (
                      <span className="home-collection__placeholder">Zeekr</span>
                    )}
                    <span className="home-collection__overlay">
                      <span className="home-collection__title">{item.title}</span>
                      <span className="home-collection__cta">{item.button_text ?? "Посмотреть"}</span>
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <PromoOffer />

      {about && <HomeAbout about={about} />}

      <section
        className={`home-map${locations.length > 0 && !mapFailed ? " home-map--live" : ""}`}
        aria-label="Контакты на карте"
      >
        {locations.length > 0 && !mapFailed ? (
          <YandexMap locations={locations} onUnavailable={() => setMapFailed(true)} />
        ) : (
          <div className="container home-map__inner">
            <div className="home-map__pin" aria-hidden="true" />
            <div className="home-map__card">
              <div>
                <Phone size={16} aria-hidden="true" />
                <span>
                  +7 (800) 551-94-31
                  <br />
                  +7 (495) 292-18-67
                </span>
              </div>
              <div>
                <Clock size={16} aria-hidden="true" />
                <span>Ежедневно с 08:00 до 21:00</span>
              </div>
              <div>
                <MapPin size={16} aria-hidden="true" />
                <span>
                  Кыргызстан
                  <br />
                  г.Бишкек, ул.Лев Толстого 30
                </span>
              </div>
              <Link to="/contacts" className="btn btn--primary">
                Как до нас добраться
              </Link>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
