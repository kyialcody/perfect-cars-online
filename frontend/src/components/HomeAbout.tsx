import { useEffect, useState } from "react";
import { Play, X } from "lucide-react";
import type { HomeAbout as HomeAboutData } from "../api/types";
import "./home-about.css";

// Extract the 11-char video id from a YouTube watch/short/embed URL, else null.
function youtubeId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([\w-]{11})/,
    /(?:youtu\.be\/)([\w-]{11})/,
    /(?:youtube\.com\/embed\/)([\w-]{11})/,
    /(?:youtube\.com\/shorts\/)([\w-]{11})/,
  ];
  for (const re of patterns) {
    const m = url.match(re);
    if (m) return m[1];
  }
  return null;
}

export default function HomeAbout({ about }: { about: HomeAboutData }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const hasVideo = Boolean(about.video_url);
  const ytId = about.video_url ? youtubeId(about.video_url) : null;
  const embed = ytId ? `https://www.youtube.com/embed/${ytId}?autoplay=1` : null;

  return (
    <section className="home-about" aria-label="О компании">
      <div className="container home-about__inner">
        <h2 className="home-about__title">О компании</h2>
        {about.description && <p className="home-about__text">{about.description}</p>}

        {hasVideo && (
          <button
            type="button"
            className="home-about__video"
            onClick={() => setOpen(true)}
            aria-label="Смотреть видео о компании"
          >
            {ytId ? (
              <img
                className="home-about__thumb"
                src={`https://img.youtube.com/vi/${ytId}/maxresdefault.jpg`}
                alt=""
                loading="lazy"
                onError={(e) => {
                  // maxres isn't generated for every video — fall back to hq.
                  const img = e.currentTarget;
                  if (!img.src.endsWith("hqdefault.jpg")) {
                    img.src = `https://img.youtube.com/vi/${ytId}/hqdefault.jpg`;
                  }
                }}
              />
            ) : (
              <video
                className="home-about__thumb"
                src={`${about.video_url}#t=0.1`}
                preload="metadata"
                muted
                playsInline
              />
            )}
            <span className="home-about__play" aria-hidden="true">
              <Play size={28} fill="currentColor" />
            </span>
          </button>
        )}
      </div>

      {open && about.video_url && (
        <div
          className="home-about__modal"
          role="dialog"
          aria-modal="true"
          aria-label="Видео о компании"
          onClick={() => setOpen(false)}
        >
          <div className="home-about__modal-body" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="home-about__close"
              onClick={() => setOpen(false)}
              aria-label="Закрыть видео"
            >
              <X size={24} aria-hidden="true" />
            </button>
            {embed ? (
              <iframe
                className="home-about__player"
                src={embed}
                title="Видео о компании"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            ) : (
              <video className="home-about__player" src={about.video_url} controls autoPlay />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
