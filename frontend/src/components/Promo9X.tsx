import { Link } from "react-router-dom";
import promoSpecs from "../assets/promo-9x-specs.png";
import promoPrice from "../assets/promo-9x-price.png";
import "./promo-9x.css";

// Promo banners for the flagship Zeekr 9X. Both cards link to the catalog
// pre-filtered to the 9X model, so a click lands on its listing.
const NINE_X_LINK = "/catalog?brand=zeekr&model=9x";

const CARDS = [
  { img: promoSpecs, alt: "Zeekr 9X — флагманский plug-in hybrid SUV" },
  { img: promoPrice, alt: "Zeekr 9X — специальная цена от 465 900 ¥ и подарок при покупке" },
];

export default function Promo9X() {
  return (
    <section className="promo-9x" aria-label="Zeekr 9X">
      {CARDS.map((card) => (
        <Link key={card.alt} to={NINE_X_LINK} className="promo-9x__card">
          <img src={card.img} alt={card.alt} loading="lazy" />
        </Link>
      ))}
    </section>
  );
}
