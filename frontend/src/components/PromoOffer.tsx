import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useLeads } from "./leads/LeadContext";
import "./promo-offer.css";

const DISCOUNT_KEY = "discount:home:10-25";

// CTA-баннер на главной (между «Наши подборки» и «О компании»).
export default function PromoOffer() {
  const [phone, setPhone] = useState("");
  const [phoneError, setPhoneError] = useState("");
  const { submitLead, isSubmitted } = useLeads();
  const sent = isSubmitted(DISCOUNT_KEY);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (sent) return;
    if (!phone.trim()) {
      setPhoneError("Введите номер телефона");
      return;
    }
    setPhoneError("");
    submitLead({
      source: "other",
      source_title: "Скидка 10–25%",
      dedupe_key: DISCOUNT_KEY,
      comment: `Телефон из формы скидки: ${phone}`,
    });
  };

  return (
    <section className="container promo-offer-wrap" aria-label="Спецпредложение">
      <div className="promo-offer">
        <div className="promo-offer__glove" aria-hidden="true" />
        <div className="promo-offer__content">
          <h2 className="promo-offer__title">Перебьём предложения от конкурентов!</h2>
          <p className="promo-offer__subtitle">
            Скидки <span className="promo-offer__accent">от 10 до 25%</span> на стоимость автомобиля
          </p>

          <form className="promo-offer__form" onSubmit={handleSubmit}>
            <input
              className="promo-offer__input"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="Ваш телефон"
              aria-label="Ваш телефон"
              value={phone}
              required
              onChange={(event) => {
                setPhone(event.target.value);
                if (phoneError) setPhoneError("");
              }}
            />
            <button type="submit" className="promo-offer__submit" disabled={sent}>
              {sent ? "Заявка отправлена" : "Получить предложение"}
            </button>
          </form>
          {phoneError && <p className="promo-offer__error">{phoneError}</p>}

          <p className="promo-offer__consent">
            Нажимая кнопку «Получить предложение», Вы принимаете{" "}
            <Link className="promo-offer__consent-accent" to="/terms">
              пользовательское соглашение
            </Link>{" "}
            и даёте согласие на обработку своих{" "}
            <Link className="promo-offer__consent-accent" to="/privacy">
              персональных данных
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}
