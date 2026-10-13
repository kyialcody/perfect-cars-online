import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { CheckCircle2, Clock3, LogOut, XCircle } from "lucide-react";
import {
  changePassword,
  listProfileLeads,
  updateProfile,
  type ProfileLead,
} from "../api/profile";
import { useAuth } from "../components/auth/AuthContext";
import "./profile.css";

const STATUS_LABEL: Record<string, string> = {
  new: "Новая",
  in_progress: "В работе",
  approved: "Одобрена",
  rejected: "Отклонена",
  done: "Завершена",
};

function StatusIcon({ status }: { status: string }) {
  if (status === "approved") return <CheckCircle2 size={18} aria-hidden="true" />;
  if (status === "rejected") return <XCircle size={18} aria-hidden="true" />;
  return <Clock3 size={18} aria-hidden="true" />;
}

export default function Profile() {
  const { user, loading, openAuth, setUser, signOut } = useAuth();
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [leads, setLeads] = useState<ProfileLead[]>([]);
  const [message, setMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name ?? "");
    setPhone(user.phone ?? "");
    listProfileLeads()
      .then(setLeads)
      .catch(() => setLeads([]));
  }, [user]);

  useEffect(() => {
    if (!loading && !user) openAuth("login");
  }, [loading, openAuth, user]);

  if (loading) return <div className="container profile-page">Загрузка профиля...</div>;
  if (!user) {
    return <Navigate to="/" replace />;
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      const next = await updateProfile({ full_name: fullName || null, phone: phone || null });
      setUser(next);
      setMessage("Данные сохранены");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Не удалось сохранить данные");
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordMessage("");
    if (newPassword !== newPasswordConfirm) {
      setPasswordMessage("Новые пароли не совпадают");
      return;
    }
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordConfirm("");
      setPasswordMessage("Пароль изменён");
    } catch (err) {
      setPasswordMessage(err instanceof Error ? err.message : "Не удалось изменить пароль");
    }
  }

  return (
    <main className="container profile-page">
      <div className="profile-page__head">
        <h1>Личный кабинет</h1>
        <button type="button" onClick={signOut}>
          <LogOut size={17} aria-hidden="true" />
          Выйти
        </button>
      </div>

      <section className="profile-card">
        <h2>Данные</h2>
        <form className="profile-form" onSubmit={save}>
          <label>
            <span>Ваше имя</span>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </label>
          <label>
            <span>Телефон</span>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" />
          </label>
          <label>
            <span>E-mail</span>
            <input value={user.email} disabled />
          </label>
          <button type="submit">Сохранить</button>
        </form>
        {message && <p className="profile-page__message">{message}</p>}
      </section>

      <section className="profile-card">
        <h2>Пароль</h2>
        <form className="profile-form profile-form--password" onSubmit={savePassword}>
          <label>
            <span>Текущий пароль</span>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <label>
            <span>Новый пароль</span>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          <label>
            <span>Подтвердите пароль</span>
            <input
              type="password"
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          <button type="submit">Изменить пароль</button>
        </form>
        {passwordMessage && <p className="profile-page__message">{passwordMessage}</p>}
      </section>

      <section className="profile-card">
        <h2>Оставленные заявки</h2>
        {leads.length === 0 ? (
          <p className="profile-empty">Заявок пока нет.</p>
        ) : (
          <div className="profile-leads">
            {leads.map((lead) => (
              <article className="profile-lead" key={lead.id}>
                {lead.car?.image_url && <img src={lead.car.image_url} alt="" />}
                <div className="profile-lead__body">
                  <div className={`profile-lead__status profile-lead__status--${lead.status}`}>
                    <StatusIcon status={lead.status} />
                    {STATUS_LABEL[lead.status] ?? lead.status}
                  </div>
                  <h3>{lead.source_title ?? "Заявка"}</h3>
                  {lead.car && <Link to={`/car/${lead.car.slug}`}>{lead.car.title}</Link>}
                  {lead.comment && <p>{lead.comment}</p>}
                  <span>{new Date(lead.created_at).toLocaleDateString("ru-RU")}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
