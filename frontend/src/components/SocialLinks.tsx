import { useEffect, useRef, useState } from "react";
import {
  Facebook,
  Globe,
  Instagram,
  MessageCircle,
  Music2,
  Phone,
  Send,
  Youtube,
  type LucideIcon,
} from "lucide-react";
import type { SocialLink } from "../api/types";
import "./social-links.css";

// Built-in icon per `kind`; an uploaded icon_url overrides this. Unknown kinds
// fall back to a generic globe.
const ICONS: Record<string, LucideIcon> = {
  telegram: Send,
  instagram: Instagram,
  whatsapp: MessageCircle,
  tiktok: Music2,
  facebook: Facebook,
  youtube: Youtube,
  phone: Phone,
};

const KIND_LABELS: Record<string, string> = {
  telegram: "Telegram",
  instagram: "Instagram",
  whatsapp: "WhatsApp",
  tiktok: "TikTok",
  facebook: "Facebook",
  youtube: "YouTube",
  vk: "ВКонтакте",
  phone: "Телефон",
};

const telHref = (value: string) => `tel:${value.replace(/[^\d+]/g, "")}`;

function SocialIcon({ social, size }: { social: SocialLink; size: number }) {
  if (social.icon_url) {
    return <img className="social-links__img" src={social.icon_url} alt="" width={size} height={size} />;
  }
  const Icon = ICONS[social.kind] ?? Globe;
  return <Icon size={size} aria-hidden="true" />;
}

/**
 * Renders the admin-managed social/contact links shared by the header and
 * footer. A `kind: "phone"` entry links straight to the single phone; with
 * several phones it opens a chooser so the user picks which one to call.
 */
export default function SocialLinks({
  socials,
  phones,
  size = 18,
  className = "",
  menuAlign = "right",
}: {
  socials: SocialLink[];
  phones: string[];
  size?: number;
  className?: string;
  // Which edge the phone chooser is anchored to, so it stays on-screen:
  // "right" when the icons sit at the right (header), "left" at the left (footer).
  menuAlign?: "left" | "right";
}) {
  const [phoneMenu, setPhoneMenu] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (phoneMenu === null) return;

    function onPointerDown(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setPhoneMenu(null);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setPhoneMenu(null);
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [phoneMenu]);

  if (socials.length === 0) return null;

  return (
    <div ref={containerRef} className={`social-links ${className}`.trim()}>
      {socials.map((social) => {
        const label = KIND_LABELS[social.kind] ?? social.kind;

        // Phone with several numbers → open a chooser instead of dialing.
        if (social.kind === "phone" && phones.length > 1) {
          const open = phoneMenu === social.id;
          return (
            <div key={social.id} className="social-links__item">
              <button
                type="button"
                className="social-links__btn"
                aria-haspopup="menu"
                aria-expanded={open}
                aria-label="Выбрать номер для звонка"
                onClick={() => setPhoneMenu(open ? null : social.id)}
              >
                <SocialIcon social={social} size={size} />
              </button>
              {open && (
                <div className={`social-links__menu social-links__menu--${menuAlign}`} role="menu">
                  {phones.map((phone) => (
                    <a key={phone} role="menuitem" href={telHref(phone)} onClick={() => setPhoneMenu(null)}>
                      {phone}
                    </a>
                  ))}
                </div>
              )}
            </div>
          );
        }

        // Phone with one number → dial it directly (fall back to a stored url).
        const href =
          social.kind === "phone"
            ? phones[0]
              ? telHref(phones[0])
              : social.url ?? "#"
            : social.url ?? "#";

        return (
          <a key={social.id} className="social-links__item" href={href} aria-label={label}>
            <SocialIcon social={social} size={size} />
          </a>
        );
      })}
    </div>
  );
}
