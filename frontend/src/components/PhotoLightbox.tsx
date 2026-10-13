import { useCallback, useEffect, type Dispatch, type SetStateAction } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import "./photo-lightbox.css";

export type LightboxPhoto = {
  id: number;
  image_url: string | null;
  alt: string | null;
};

type Direction = -1 | 1;

/**
 * Fullscreen photo viewer with prev/next, counter, keyboard (Esc/←/→) and body
 * scroll-lock. Controlled: render `null` index to keep it closed. `photos`
 * should already be filtered to entries that have an `image_url`.
 */
export default function PhotoLightbox({
  photos,
  index,
  setIndex,
  label = "Просмотр фото",
}: {
  photos: LightboxPhoto[];
  index: number | null;
  setIndex: Dispatch<SetStateAction<number | null>>;
  label?: string;
}) {
  const close = useCallback(() => setIndex(null), [setIndex]);
  const step = useCallback(
    (direction: Direction) => {
      setIndex((current) => {
        if (current === null || photos.length === 0) return current;
        return (current + direction + photos.length) % photos.length;
      });
    },
    [setIndex, photos.length],
  );

  useEffect(() => {
    if (index === null) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") close();
      else if (event.key === "ArrowRight") step(1);
      else if (event.key === "ArrowLeft") step(-1);
    }

    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [index, close, step]);

  if (index === null) return null;
  const active = photos[index];
  if (!active || !active.image_url) return null;

  return (
    <div
      className="photo-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={label}
      onClick={close}
    >
      <button type="button" className="photo-lightbox__close" aria-label="Закрыть" onClick={close}>
        <X size={24} aria-hidden="true" />
      </button>

      {photos.length > 1 && (
        <button
          type="button"
          className="photo-lightbox__nav photo-lightbox__nav--prev"
          aria-label="Предыдущее фото"
          onClick={(event) => {
            event.stopPropagation();
            step(-1);
          }}
        >
          <ChevronLeft size={28} aria-hidden="true" />
        </button>
      )}

      <figure className="photo-lightbox__figure" onClick={(event) => event.stopPropagation()}>
        <img src={active.image_url} alt={active.alt ?? label} />
        {photos.length > 1 && (
          <figcaption className="photo-lightbox__counter">
            {index + 1} / {photos.length}
          </figcaption>
        )}
      </figure>

      {photos.length > 1 && (
        <button
          type="button"
          className="photo-lightbox__nav photo-lightbox__nav--next"
          aria-label="Следующее фото"
          onClick={(event) => {
            event.stopPropagation();
            step(1);
          }}
        >
          <ChevronRight size={28} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
