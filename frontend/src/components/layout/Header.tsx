import { useEffect, useState } from "react";
import { NavLink, Link, useLocation, type Location } from "react-router-dom";
import { ChevronRight, Clock, MapPin, Menu, Phone, Search, User, X } from "lucide-react";
import { getContactsPage } from "../../api/home";
import type { ContactPage } from "../../api/types";
import { useAuth } from "../auth/AuthContext";
import SocialLinks from "../SocialLinks";
import logo from "../../assets/header-logo.png";
import "./header.css";

const FALLBACK_HEADER_ADDRESS = "Кыргызстан, г. Бишкек, ул. Лев Толстого 30";
const FALLBACK_PHONES = ["+7 (800) 551-94-31", "+7 (495) 292-18-67"];
const WORKING_HOURS = "с 08:00 до 21:00";

// Two-row header per docs/design/header.png.
// «Авто с пробегом» reuses the catalog filtered to used (no separate route).
// Both catalog entries share the `/catalog` pathname, so NavLink's default
// (pathname-only) active check can't tell them apart — each carries a `match`
// that also looks at the `condition` query param.
const usedParam = (loc: Location) =>
  new URLSearchParams(loc.search).get("condition") === "used";

const MENU: {
  to: string;
  label: string;
  match?: (loc: Location) => boolean;
}[] = [
  {
    to: "/catalog",
    label: "Каталог авто",
    match: (loc) => loc.pathname === "/catalog" && !usedParam(loc),
  },
  {
    to: "/used",
    label: "Авто с пробегом",
    match: (loc) => loc.pathname === "/used",
  },
  { to: "/parts", label: "Запчасти" },
  { to: "/special", label: "Спецпредложения" },
];

// Secondary links — match the desktop top-row entries (Техцентр / Отзывы are
// intentionally omitted until those pages exist).
const SECONDARY: { to: string; label: string }[] = [
  { to: "/select", label: "Подбор авто" },
  { to: "/about", label: "О компании" },
  { to: "/contacts", label: "Контакты" },
];

export default function Header() {
  const location = useLocation();
  const { user, openAuth } = useAuth();
  const [contacts, setContacts] = useState<ContactPage | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    getContactsPage()
      .then(setContacts)
      .catch(() => setContacts(null));
  }, []);

  // Close the mobile drawer whenever navigation happens.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname, location.search]);

  // Lock background scroll while the drawer is open.
  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  // Header shows the addresses the admin flagged with show_in_header (any
  // number). Until contacts load, fall back to the static address to avoid a
  // flash of empty space.
  const headerAddresses = contacts
    ? contacts.addresses.filter((address) => address.show_in_header).map((address) => address.value)
    : [FALLBACK_HEADER_ADDRESS];
  const phones = contacts?.phones.map((phone) => phone.value) ?? [];
  const socials = contacts?.socials ?? [];

  // Drawer contacts use sensible fallbacks so the card is never blank.
  const drawerPhones = phones.length > 0 ? phones : FALLBACK_PHONES;
  const drawerAddresses =
    contacts && contacts.addresses.length > 0
      ? contacts.addresses.map((address) => address.value)
      : [FALLBACK_HEADER_ADDRESS];

  return (
    <header className="site-header">
      {/* Collapsed bar shown on phones: burger · logo · search · location. */}
      <div className="site-header__mobile">
        <div className="container site-header__mobile-inner">
          <button
            type="button"
            className="site-header__icon-btn site-header__burger"
            aria-label="Открыть меню"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={26} aria-hidden="true" />
          </button>
          <Link to="/" className="site-header__logo site-header__logo--mobile" aria-label="Electro-avto — на главную">
            <img src={logo} alt="Electro-avto" />
          </Link>
          <div className="site-header__mobile-actions">
            <Link to="/search" className="site-header__icon-btn" aria-label="Поиск">
              <Search size={22} aria-hidden="true" />
            </Link>
            <Link to="/contacts" className="site-header__icon-btn" aria-label="Контакты и адрес">
              <MapPin size={22} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>

      <div className="site-header__top">
        <div className="container site-header__top-inner">
          <Link to="/" className="site-header__logo" aria-label="Electro-avto — на главную">
            <img src={logo} alt="Electro-avto — 5 лет превосходим ваши ожидания" />
          </Link>
          <nav className="site-header__top-links">
            <NavLink to="/select">Подбор авто</NavLink>
            <NavLink to="/about">О компании</NavLink>
            <NavLink to="/contacts">Контакты</NavLink>
          </nav>
          {headerAddresses.length > 0 && (
            <div className="site-header__location">
              <MapPin size={16} aria-hidden="true" />
              <span>
                {headerAddresses.map((address) => (
                  <span key={address}>{address}</span>
                ))}
              </span>
            </div>
          )}
          {user ? (
            <Link to="/profile" className="site-header__login" aria-label="Личный кабинет">
              <User size={22} aria-hidden="true" />
              <span>Профиль</span>
            </Link>
          ) : (
            <button type="button" className="site-header__login" aria-label="Войти" onClick={() => openAuth("login")}>
              <User size={22} aria-hidden="true" />
              <span>Войти</span>
            </button>
          )}
        </div>
      </div>

      <div className="site-header__menu">
        <div className="container site-header__menu-inner">
          <nav className="site-header__nav">
            {MENU.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                // A function className fully controls the class (v6 won't
                // auto-add "active"); `isActive` is used only for entries
                // without a custom `match`.
                className={({ isActive }) =>
                  (item.match ? item.match(location) : isActive) ? "active" : ""
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <SocialLinks socials={socials} phones={phones} size={18} className="site-header__socials" />
        </div>
      </div>

      {/* Mobile drawer («меню управления»). */}
      <div
        className={`site-header__overlay${menuOpen ? " is-open" : ""}`}
        onClick={() => setMenuOpen(false)}
        aria-hidden="true"
      />
      <nav
        className={`site-header__drawer${menuOpen ? " is-open" : ""}`}
        aria-label="Меню"
        aria-hidden={!menuOpen}
      >
        <div className="site-header__drawer-head">
          <Link to="/" className="site-header__logo">
            <img src={logo} alt="Electro-avto" />
          </Link>
          <button
            type="button"
            className="site-header__icon-btn"
            aria-label="Закрыть меню"
            onClick={() => setMenuOpen(false)}
          >
            <X size={24} aria-hidden="true" />
          </button>
        </div>

        <ul className="site-header__drawer-primary">
          {MENU.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  (item.match ? item.match(location) : isActive) ? "active" : ""
                }
              >
                <ChevronRight size={18} aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>

        <ul className="site-header__drawer-secondary">
          {SECONDARY.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to}>{item.label}</NavLink>
            </li>
          ))}
        </ul>

        {user ? (
          <Link to="/profile" className="site-header__drawer-login" aria-label="Личный кабинет">
            <User size={20} aria-hidden="true" />
            <span>Личный кабинет</span>
          </Link>
        ) : (
          <button
            type="button"
            className="site-header__drawer-login"
            aria-label="Войти в аккаунт"
            onClick={() => {
              setMenuOpen(false);
              openAuth("login");
            }}
          >
            <User size={20} aria-hidden="true" />
            <span>Войти в аккаунт</span>
          </button>
        )}

        <div className="site-header__drawer-contacts">
          <div className="site-header__drawer-contact">
            <span className="site-header__drawer-ico">
              <Phone size={15} aria-hidden="true" />
            </span>
            <span className="site-header__drawer-lines">
              {drawerPhones.map((phone) => (
                <a key={phone} href={`tel:${phone.replace(/[^\d+]/g, "")}`}>
                  {phone}
                </a>
              ))}
            </span>
          </div>
          <div className="site-header__drawer-contact">
            <span className="site-header__drawer-ico">
              <Clock size={15} aria-hidden="true" />
            </span>
            <span className="site-header__drawer-lines">{WORKING_HOURS}</span>
          </div>
          <div className="site-header__drawer-contact">
            <span className="site-header__drawer-ico">
              <MapPin size={15} aria-hidden="true" />
            </span>
            <span className="site-header__drawer-lines">
              {drawerAddresses.map((address) => (
                <span key={address}>{address}</span>
              ))}
            </span>
          </div>
        </div>
      </nav>
    </header>
  );
}
