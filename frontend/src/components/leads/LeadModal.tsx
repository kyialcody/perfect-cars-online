import { X } from "lucide-react";
import type { LeadPayload } from "../../api/leads";
import "./lead-modal.css";

export default function LeadModal({
  confirmPayload,
  busy,
  error,
  success,
  onConfirm,
  onCancel,
  onSuccessClose,
}: {
  confirmPayload: Omit<LeadPayload, "name" | "phone" | "consent"> | null;
  busy: boolean;
  error: string;
  success: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  onSuccessClose: () => void;
}) {
  if (!confirmPayload && !success) return null;

  if (success) {
    return (
      <div className="lead-modal" role="dialog" aria-modal="true" onClick={onSuccessClose}>
        <div className="lead-modal__panel lead-modal__panel--success" onClick={(e) => e.stopPropagation()}>
          <button type="button" className="lead-modal__close" aria-label="Закрыть" onClick={onSuccessClose}>
            <X size={25} aria-hidden="true" />
          </button>
          <h2>Спасибо за обращение!</h2>
          <p>Наш менеджер свяжется с Вами в ближайшее время</p>
          <button type="button" className="lead-modal__primary" onClick={onSuccessClose}>
            Ok
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="lead-modal" role="dialog" aria-modal="true" onClick={onCancel}>
      <div className="lead-modal__panel" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="lead-modal__close" aria-label="Закрыть" onClick={onCancel}>
          <X size={25} aria-hidden="true" />
        </button>
        <h2>Подать заявку?</h2>
        <p>{confirmPayload?.source_title ?? "Менеджер свяжется с вами для уточнения деталей."}</p>
        {error && <p className="lead-modal__error">{error}</p>}
        <div className="lead-modal__actions">
          <button type="button" className="lead-modal__secondary" onClick={onCancel}>
            Отмена
          </button>
          <button type="button" className="lead-modal__primary" onClick={onConfirm} disabled={busy}>
            {busy ? "Отправляем..." : "Да, подать"}
          </button>
        </div>
      </div>
    </div>
  );
}
