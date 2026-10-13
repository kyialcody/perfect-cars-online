import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";
import { ApiError } from "../../api/client";
import type { LoginPayload, RegisterPayload } from "../../api/auth";
import "./auth-modal.css";

function errorText(error: unknown) {
  if (error instanceof ApiError) {
    if (typeof error.message === "string" && error.message.includes("GMAIL_FORBIDDEN")) {
      return "По законодательству РФ нельзя зарегистрироваться через @gmail.com";
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "Не удалось выполнить действие";
}

function isBlockedEmail(email: string) {
  const domain = email.split("@").pop()?.toLowerCase();
  return domain === "gmail.com" || domain === "googlemail.com";
}

export default function AuthModal({
  mode,
  onClose,
  onLogin,
  onRegister,
}: {
  mode: "login" | "register" | null;
  onClose: () => void;
  onLogin: (payload: LoginPayload) => Promise<void>;
  onRegister: (payload: RegisterPayload) => Promise<void>;
}) {
  const [view, setView] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (mode) {
      setView(mode);
      setError("");
      setAccepted(false);
    }
  }, [mode]);

  if (!mode) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (view === "register" && isBlockedEmail(email)) {
      setError("По законодательству РФ нельзя зарегистрироваться через @gmail.com");
      return;
    }
    if (view === "register" && password !== passwordConfirm) {
      setError("Пароли не совпадают");
      return;
    }
    if (view === "register" && !accepted) {
      setError("Необходимо принять пользовательское соглашение и политику конфиденциальности");
      return;
    }
    setBusy(true);
    try {
      if (view === "login") {
        await onLogin({ email, password });
      } else {
        await onRegister({ email, password, full_name: fullName, phone });
      }
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-modal" role="dialog" aria-modal="true" onClick={onClose}>
      <form className="auth-modal__panel" onSubmit={submit} onClick={(e) => e.stopPropagation()}>
        <button type="button" className="auth-modal__close" aria-label="Закрыть" onClick={onClose}>
          <X size={25} aria-hidden="true" />
        </button>
        <h2>{view === "login" ? "Войти" : "Регистрация"}</h2>
        {view === "register" && (
          <>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Ваше имя"
              autoComplete="name"
              required
            />
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Контактный телефон"
              inputMode="tel"
              autoComplete="tel"
              required
            />
          </>
        )}
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="E-mail"
          type="email"
          autoComplete="email"
          required
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Пароль"
          type="password"
          autoComplete={view === "login" ? "current-password" : "new-password"}
          minLength={view === "register" ? 8 : 1}
          required
        />
        {view === "register" && (
          <input
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            placeholder="Подтвердите пароль"
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
          />
        )}
        {view === "register" && (
          <p className="auth-modal__note">
            По законодательству РФ нельзя зарегистрироваться через @gmail.com.
          </p>
        )}
        {view === "register" && (
          <label className="auth-modal__consent">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
            />
            <span>
              Я принимаю{" "}
              <Link to="/terms" onClick={onClose}>
                пользовательское соглашение
              </Link>{" "}
              и{" "}
              <Link to="/privacy" onClick={onClose}>
                политику конфиденциальности
              </Link>
            </span>
          </label>
        )}
        {error && <p className="auth-modal__error">{error}</p>}
        <button
          type="submit"
          className="auth-modal__submit"
          disabled={busy || (view === "register" && !accepted)}
        >
          {busy ? "Подождите..." : view === "login" ? "Войти" : "Зарегистрироваться"}
        </button>
        <button
          type="button"
          className="auth-modal__switch"
          onClick={() => {
            setError("");
            setAccepted(false);
            setView(view === "login" ? "register" : "login");
          }}
        >
          {view === "login" ? "Создать аккаунт" : "Уже есть аккаунт"}
        </button>
      </form>
    </div>
  );
}
