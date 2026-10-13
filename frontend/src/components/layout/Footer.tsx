import { useEffect, useState } from "react";
import { NavLink, useLocation, type Location } from "react-router-dom";
import { Phone, Clock, MapPin } from "lucide-react";
import { getContactsPage } from "../../api/home";
import type { ContactPage, Requisite } from "../../api/types";
import SocialLinks from "../SocialLinks";
import logo from "../../assets/footer-logo.png";
import "./footer.css";

// Fallbacks shown only if the admin-managed Contacts content is empty or fails
// to load, so the footer never renders blank.
const FALLBACK_PHONES = ["+7 (800) 551-94-31", "+7 (495) 292-18-67"];
const FALLBACK_ADDRESSES = ["Кыргызстан, г. Бишкек, ул. Лев Толстого 30"];
const FALLBACK_FOOTER_TEXT =
  "Мы располагаем огромной торговой площадкой более 5000 квадратных метров, у нас " +
  "в наличии не менее 200 автомобилей как отечественного, так и иностранного " +
  "производства. В штате автосалона «Альтера» работают настоящие профессионалы, " +
  "которые знают особенности каждого конкретного автомобиля.";

// Footer per docs/design/footer.png. Requisites/contacts are placeholder data
// copied from the design reference.
const MENU: {
  to: string;
  label: string;
  match?: (loc: Location) => boolean;
}[] = [
  {
    to: "/catalog",
    label: "Каталог авто",
    match: (loc: Location) =>
      loc.pathname === "/catalog" && new URLSearchParams(loc.search).get("condition") !== "used",
  },
  {
    to: "/used",
    label: "Авто с пробегом",
    match: (loc: Location) => loc.pathname === "/used",
  },
  { to: "/parts", label: "Запчасти" },
  { to: "/special", label: "Спецпредложения" },
];

// Fallback requisites — used only when the admin hasn't entered any.
const FALLBACK_REQUISITES: { label: string; value: string }[] = [
  { label: "Полное название организации", value: 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ARENDA"' },
  { label: "Английское название", value: 'ООО "ARENDA"' },
  { label: "Адрес", value: "Красноярский кр., г. Красноярск, ул. Молокова, д. 56 стр. 1" },
  { label: "Уставный капитал", value: "10 000" },
  { label: "ОКФС", value: "Частная собственность" },
  { label: "ОКОПФ", value: "Общества с ограниченной ответственностью" },
  {
    label: "ОКОГУ",
    value:
      "Организации, учрежденные юридическими лицами или гражданами, или юридическими лицами и гражданами совместно",
  },
  { label: "ИНН", value: "2463087637" },
  { label: "ОГРН", value: "1072463005537" },
  { label: "КПП", value: "246501001" },
  { label: "ОКАТО", value: "Красноярский край, Красноярск, Советский" },
  { label: "ОКПО", value: "81213568" },
  { label: "ОКТМО", value: "Красноярский край, Городские округа Красноярского края, г Красноярск" },
];

export default function Footer() {
  const location = useLocation();
  const [contacts, setContacts] = useState<ContactPage | null>(null);

  useEffect(() => {
    getContactsPage()
      .then(setContacts)
      .catch(() => setContacts(null));
  }, []);

  const phones = contacts?.phones.length
    ? contacts.phones.map((phone) => phone.value)
    : FALLBACK_PHONES;
  const addresses = contacts?.addresses.length
    ? contacts.addresses.map((address) => address.value)
    : FALLBACK_ADDRESSES;
  const requisites: Pick<Requisite, "label" | "value">[] = contacts?.requisites.length
    ? contacts.requisites
    : FALLBACK_REQUISITES;
  const footerText = contacts?.footer_about_text || FALLBACK_FOOTER_TEXT;
  const socials = contacts?.socials ?? [];

  return (
    <footer className="site-footer">
      <div className="container">
        <nav className="site-footer__nav">
          <div className="site-footer__nav-menu">
            {MENU.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  (item.match ? item.match(location) : isActive) ? "active" : ""
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
          <span className="site-footer__nav-contacts">Контакты</span>
        </nav>

        <div className="site-footer__cols">
          <div className="site-footer__col">
            <img className="site-footer__logo" src={logo} alt="Electro-avto" />
            <p>{footerText}</p>
          </div>

          <div className="site-footer__col site-footer__requisites">
            <h4>Реквизиты</h4>
            <dl>
              {requisites.map((r) => (
                <div key={r.label} className="site-footer__requisite">
                  <dt>{r.label}</dt>
                  <dd>{r.value}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="site-footer__col site-footer__contacts">
            <div className="site-footer__contact">
              <Phone size={16} aria-hidden="true" />
              <span>
                {phones.map((phone) => (
                  <a key={phone} href={`tel:${phone.replace(/[^\d+]/g, "")}`}>
                    {phone}
                  </a>
                ))}
              </span>
            </div>
            <div className="site-footer__contact">
              <Clock size={16} aria-hidden="true" />
              <span>Ежедневно с 08:00 до 21:00</span>
            </div>
            <div className="site-footer__contact">
              <MapPin size={16} aria-hidden="true" />
              <span>
                {addresses.map((address) => (
                  <span key={address}>{address}</span>
                ))}
              </span>
            </div>

            {socials.length > 0 && (
              <>
                <div className="site-footer__socials-label">Соц. сети:</div>
                <SocialLinks
                  socials={socials}
                  phones={phones}
                  size={18}
                  className="site-footer__socials"
                  menuAlign="left"
                />
              </>
            )}
          </div>
        </div>

        <p className="site-footer__legal">
          Индивидуальный предприниматель Ибраева Кыял Бактыбековна
        </p>
      </div>
    </footer>
  );
}
