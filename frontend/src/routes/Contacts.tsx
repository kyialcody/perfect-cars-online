import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, MapPin, Phone } from "lucide-react";
import { getContactsPage, getLocations } from "../api/home";
import type { ContactPage, ContactPhoto, DealerLocation } from "../api/types";
import PhotoLightbox from "../components/PhotoLightbox";
import YandexMap from "../components/YandexMap";
import "./contacts.css";

type ViewablePhoto = ContactPhoto & { image_url: string };

function renderText(text: string | null) {
  if (!text) return null;
  return text
    .split(/\n{2,}/)
    .map((block) => block.split("\n").map((line) => line.trim()).filter(Boolean).join(" "))
    .filter(Boolean)
    .map((paragraph) => <p key={paragraph}>{paragraph}</p>);
}

export default function Contacts() {
  const [data, setData] = useState<ContactPage | null>(null);
  const [failed, setFailed] = useState(false);
  const [locations, setLocations] = useState<DealerLocation[]>([]);
  const [mapFailed, setMapFailed] = useState(false);
  const [slide, setSlide] = useState(0);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  useEffect(() => {
    getContactsPage()
      .then((res) => {
        setData(res);
        setFailed(false);
      })
      .catch(() => {
        setData(null);
        setFailed(true);
      });
    getLocations()
      .then(setLocations)
      .catch(() => setLocations([]));
  }, []);

  const phones = data?.phones ?? [];
  const addresses = data?.addresses ?? [];
  const about = useMemo(() => renderText(data?.about_text ?? null), [data]);
  const photos = useMemo(() => data?.photos ?? [], [data]);
  const viewablePhotos = useMemo(
    () => photos.filter((photo): photo is ViewablePhoto => Boolean(photo.image_url)),
    [photos],
  );

  // Keep the carousel index in range when the photo set changes.
  const current = viewablePhotos.length > 0 ? slide % viewablePhotos.length : 0;
  const activePhoto = viewablePhotos[current];

  function move(direction: -1 | 1) {
    if (viewablePhotos.length === 0) return;
    setSlide((value) => (value + direction + viewablePhotos.length) % viewablePhotos.length);
  }

  return (
    <main className="contacts-page">
      <div className="container">
        <h1>Контакты</h1>

        {failed && (
          <p className="contacts-page__muted">Не удалось загрузить контактную информацию.</p>
        )}

        <section className="contacts-head" aria-label="Контактная информация">
          {phones.length > 0 && (
            <div className="contacts-head__block">
              <div className="contacts-head__title">
                <Phone size={18} aria-hidden="true" />
                <span>Телефон</span>
              </div>
              <div className="contacts-head__values">
                {phones.map((phone) => (
                  <a key={phone.id} href={`tel:${phone.value.replace(/[^\d+]/g, "")}`}>
                    {phone.value}
                  </a>
                ))}
              </div>
            </div>
          )}

          {addresses.length > 0 && (
            <div className="contacts-head__block">
              <div className="contacts-head__title">
                <MapPin size={18} aria-hidden="true" />
                <span>Адрес</span>
              </div>
              <div className="contacts-head__values">
                {addresses.map((address) => (
                  <span key={address.id}>{address.value}</span>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>

      {locations.length > 0 && !mapFailed && (
        <section className="contacts-map" aria-label="Контакты на карте">
          <YandexMap locations={locations} onUnavailable={() => setMapFailed(true)} />
        </section>
      )}

      {(about || viewablePhotos.length > 0) && (
        <section className="container contacts-about" aria-label="О компании">
          <h2>О компании</h2>
          <div className="contacts-about__grid">
            <div className="contacts-about__text">
              {about ?? <p>Информация о компании скоро появится.</p>}
            </div>

            {activePhoto && (
              <div className="contacts-gallery">
                <button
                  type="button"
                  className="contacts-gallery__photo"
                  onClick={() => setLightboxIndex(current)}
                  aria-label={`Открыть фото${activePhoto.alt ? `: ${activePhoto.alt}` : ""}`}
                >
                  <img src={activePhoto.image_url} alt={activePhoto.alt ?? "Фото автосалона"} />
                </button>

                {viewablePhotos.length > 1 && (
                  <>
                    <button
                      type="button"
                      className="contacts-gallery__arrow contacts-gallery__arrow--prev"
                      aria-label="Предыдущее фото"
                      onClick={() => move(-1)}
                    >
                      <ChevronLeft size={28} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      className="contacts-gallery__arrow contacts-gallery__arrow--next"
                      aria-label="Следующее фото"
                      onClick={() => move(1)}
                    >
                      <ChevronRight size={28} aria-hidden="true" />
                    </button>
                    <div className="contacts-gallery__bar" aria-hidden="true">
                      {viewablePhotos.map((photo, index) => (
                        <span key={photo.id} className={index === current ? "is-active" : ""} />
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      <PhotoLightbox
        photos={viewablePhotos}
        index={lightboxIndex}
        setIndex={setLightboxIndex}
        label="Просмотр фото автосалона"
      />
    </main>
  );
}
