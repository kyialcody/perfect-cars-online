import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getAboutPage } from "../api/home";
import type { AboutPage, AboutSalonPhoto, BankPartner } from "../api/types";
import PhotoLightbox from "../components/PhotoLightbox";
import "./about.css";

type Direction = -1 | 1;
type ScrollState = {
  photos: boolean;
  banks: boolean;
};

function renderText(text: string | null) {
  if (!text) return null;
  return text.split(/\n{2,}/).map((block) => {
    const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
    const bullets = lines
      .filter((line) => line.startsWith("•") || line.startsWith("-"))
      .map((line) => line.replace(/^[•-]\s*/, ""));
    if (bullets.length === lines.length && bullets.length > 0) {
      return (
        <ul key={block}>
          {bullets.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      );
    }
    return <p key={block}>{lines.join(" ")}</p>;
  });
}

function CarouselNav({
  onMove,
  disabled,
}: {
  onMove: (direction: Direction) => void;
  disabled: boolean;
}) {
  return (
    <div className="about-carousel__nav">
      <button type="button" aria-label="Назад" onClick={() => onMove(-1)} disabled={disabled}>
        <ChevronLeft size={18} aria-hidden="true" />
      </button>
      <button type="button" aria-label="Вперёд" onClick={() => onMove(1)} disabled={disabled}>
        <ChevronRight size={18} aria-hidden="true" />
      </button>
    </div>
  );
}

export default function About() {
  const [data, setData] = useState<AboutPage | null>(null);
  const [failed, setFailed] = useState(false);
  const [scrollable, setScrollable] = useState<ScrollState>({ photos: false, banks: false });
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const photosRef = useRef<HTMLDivElement>(null);
  const banksRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getAboutPage()
      .then((res) => {
        setData(res);
        setFailed(false);
      })
      .catch(() => {
        setData(null);
        setFailed(true);
      });
  }, []);

  const text = useMemo(() => renderText(data?.page_text ?? data?.description ?? null), [data]);
  const photos = useMemo(() => data?.photos ?? [], [data]);
  const banks = data?.banks ?? [];
  const viewablePhotos = useMemo(
    () => photos.filter((photo): photo is AboutSalonPhoto & { image_url: string } => Boolean(photo.image_url)),
    [photos],
  );

  useEffect(() => {
    function measure() {
      const photosNode = photosRef.current;
      const banksNode = banksRef.current;
      setScrollable({
        photos: Boolean(photosNode && photosNode.scrollWidth > photosNode.clientWidth + 1),
        banks: Boolean(banksNode && banksNode.scrollWidth > banksNode.clientWidth + 1),
      });
    }

    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [photos.length, banks.length]);

  function scroll(ref: React.RefObject<HTMLDivElement>, direction: Direction) {
    const node = ref.current;
    if (!node) return;
    node.scrollBy({ left: direction * node.clientWidth * 0.86, behavior: "smooth" });
  }

  return (
    <main className="container about-page">
      <h1>О компании</h1>

      {failed && <p className="about-page__muted">Не удалось загрузить информацию о компании.</p>}

      <section className="about-page__content">
        {text ?? (
          <p>
            Electro-avto помогает подобрать автомобиль под ваш сценарий, бюджет и сроки.
            Мы сопровождаем клиента от консультации до выдачи автомобиля.
          </p>
        )}
      </section>

      {photos.length > 0 && (
        <section className="about-carousel" aria-label="Фото автосалона">
          <div className="about-carousel__head">
            <h2>Фото - автосалона</h2>
            <CarouselNav onMove={(direction) => scroll(photosRef, direction)} disabled={!scrollable.photos} />
          </div>
          <div className="about-carousel__track about-carousel__track--photos" ref={photosRef}>
            {photos.map((photo: AboutSalonPhoto) => {
              const viewIndex = photo.image_url
                ? viewablePhotos.findIndex((item) => item.id === photo.id)
                : -1;
              return (
                <article className="about-photo" key={photo.id}>
                  {photo.image_url ? (
                    <button
                      type="button"
                      className="about-photo__open"
                      onClick={() => setLightboxIndex(viewIndex)}
                      aria-label={`Открыть фото${photo.alt ? `: ${photo.alt}` : ""}`}
                    >
                      <img src={photo.image_url} alt={photo.alt ?? "Фото автосалона"} loading="lazy" />
                    </button>
                  ) : (
                    <span>{photo.alt ?? "Фото автосалона"}</span>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}

      {banks.length > 0 && (
        <section className="about-carousel" aria-label="Банки партнёры">
          <div className="about-carousel__head">
            <h2>Банки - партнеры</h2>
            <CarouselNav onMove={(direction) => scroll(banksRef, direction)} disabled={!scrollable.banks} />
          </div>
          <div className="about-carousel__track about-carousel__track--banks" ref={banksRef}>
            {banks.map((bank: BankPartner) => (
              <article className="about-bank" key={bank.id}>
                {bank.logo_url ? (
                  <img src={bank.logo_url} alt={bank.name} loading="lazy" />
                ) : (
                  <span>{bank.name}</span>
                )}
              </article>
            ))}
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
