import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import type { ImageOut } from "../../api/types";

// Side thumbnails are a vertical carousel: only THUMBS_PER_PAGE are visible at a
// time; the strip slides by one page (height kept in sync with car-page.css).
const THUMBS_PER_PAGE = 4;
const THUMB_HEIGHT = 100;
const THUMB_GAP = 10;
const THUMBS_PAGE_PX = THUMBS_PER_PAGE * (THUMB_HEIGHT + THUMB_GAP);

function NavButton({
  dir,
  size,
  onActivate,
  className,
}: {
  dir: 1 | -1;
  size: number;
  onActivate: () => void;
  className?: string;
}) {
  const Icon = dir === -1 ? ChevronLeft : ChevronRight;
  return (
    <button
      type="button"
      className={className}
      aria-label={dir === -1 ? "Предыдущее фото" : "Следующее фото"}
      onClick={(event) => {
        event.stopPropagation();
        onActivate();
      }}
    >
      <Icon size={size} aria-hidden="true" />
    </button>
  );
}

// Shared photo gallery with a main stage, a vertical thumbnail carousel and a
// keyboard/touch-driven lightbox. Used by both the car and part detail pages.
export default function Gallery({
  images,
  title,
  heading = `Фото ${title}`,
  variant,
}: {
  images: ImageOut[];
  title: string;
  heading?: string | null;
  variant?: "used";
}) {
  const [current, setCurrent] = useState(0);
  const [lightbox, setLightbox] = useState(false);
  const touchX = useRef<number | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const safeImages = images.length > 0 ? images : [];
  const image = safeImages[current];
  const thumbsPage = Math.floor(current / THUMBS_PER_PAGE);

  const go = useCallback(
    (direction: 1 | -1) => {
      setCurrent((value) =>
        safeImages.length === 0 ? 0 : (value + direction + safeImages.length) % safeImages.length,
      );
    },
    [safeImages.length],
  );

  useEffect(() => {
    if (!lightbox) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setLightbox(false);
      else if (event.key === "ArrowLeft") go(-1);
      else if (event.key === "ArrowRight") go(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox, go]);

  useEffect(() => {
    if (lightbox) closeRef.current?.focus();
  }, [lightbox]);

  const onTouchStart = (event: React.TouchEvent) => {
    touchX.current = event.touches[0]?.clientX ?? null;
  };
  const onTouchEnd = (event: React.TouchEvent) => {
    if (touchX.current == null) return;
    const dx = (event.changedTouches[0]?.clientX ?? touchX.current) - touchX.current;
    if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
    touchX.current = null;
  };

  return (
    <section
      className={`car-detail__gallery${variant === "used" ? " car-detail__gallery--used" : ""}`}
      aria-label={heading ?? `Фото ${title}`}
    >
      {heading && <h2>{heading}</h2>}
      <div className="car-gallery">
        <div className="car-gallery__stage" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
          {image ? (
            <img
              src={image.url}
              alt={title}
              role="button"
              tabIndex={0}
              aria-label="Открыть фото на весь экран"
              onClick={() => setLightbox(true)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setLightbox(true);
                }
              }}
            />
          ) : (
            <div className="car-gallery__empty">Фото скоро появятся</div>
          )}
          {safeImages.length > 1 && (
            <>
              <NavButton dir={-1} size={20} onActivate={() => go(-1)} />
              <NavButton dir={1} size={20} onActivate={() => go(1)} />
            </>
          )}
        </div>
        <div className="car-gallery__thumbs">
          <div
            className="car-gallery__thumbs-track"
            style={{ "--thumb-offset": `${-thumbsPage * THUMBS_PAGE_PX}px` } as React.CSSProperties}
          >
            {safeImages.map((item, index) => (
              <button
                type="button"
                key={`${item.url}-${index}`}
                className={index === current ? "is-active" : ""}
                onClick={() => setCurrent(index)}
                aria-label={`Фото ${index + 1}`}
              >
                <img src={item.url} alt="" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {lightbox && image && (
        <div className="car-lightbox" role="dialog" aria-modal="true" onClick={() => setLightbox(false)}>
          <button
            ref={closeRef}
            type="button"
            className="car-lightbox__close"
            aria-label="Закрыть"
            onClick={() => setLightbox(false)}
          >
            <X size={28} aria-hidden="true" />
          </button>
          {safeImages.length > 1 && (
            <NavButton
              dir={-1}
              size={32}
              className="car-lightbox__nav car-lightbox__nav--prev"
              onActivate={() => go(-1)}
            />
          )}
          <img src={image.url} alt={title} onClick={(event) => event.stopPropagation()} />
          {safeImages.length > 1 && (
            <NavButton
              dir={1}
              size={32}
              className="car-lightbox__nav car-lightbox__nav--next"
              onActivate={() => go(1)}
            />
          )}
        </div>
      )}
    </section>
  );
}
