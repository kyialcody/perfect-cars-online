import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./cookie-consent.css";

const STORAGE_KEY = "cookie-consent";
type Decision = "accepted" | "declined";

// Всплывающая снизу панель о cookie и политике конфиденциальности. Показывается
// один раз до первого выбора; решение запоминается в localStorage.
export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved !== "accepted" && saved !== "declined") setVisible(true);
    } catch {
      setVisible(true);
    }
  }, []);

  function decide(decision: Decision) {
    try {
      window.localStorage.setItem(STORAGE_KEY, decision);
    } catch {
      /* private mode / storage disabled — просто закрываем */
    }
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="cookie-consent" role="dialog" aria-live="polite" aria-label="Согласие на использование cookie">
      <p className="cookie-consent__text">
        Мы используем файлы cookie для работы сайта и улучшения его удобства. Продолжая
        пользоваться сайтом, вы принимаете{" "}
        <Link to="/privacy">политику конфиденциальности</Link> и{" "}
        <Link to="/terms">пользовательское соглашение</Link>.
      </p>
      <div className="cookie-consent__actions">
        <button type="button" className="cookie-consent__decline" onClick={() => decide("declined")}>
          Отклонить
        </button>
        <button type="button" className="cookie-consent__accept" onClick={() => decide("accepted")}>
          Принять
        </button>
      </div>
    </div>
  );
}
