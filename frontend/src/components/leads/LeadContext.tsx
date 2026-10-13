import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createLead, type LeadPayload } from "../../api/leads";
import { listProfileLeads } from "../../api/profile";
import { useAuth } from "../auth/AuthContext";
import LeadModal from "./LeadModal";

interface SubmitOptions {
  confirm?: boolean;
}

type LeadDraft = Omit<LeadPayload, "name" | "phone" | "consent"> & {
  contactName?: string;
  contactPhone?: string;
};

interface LeadContextValue {
  submitLead: (payload: LeadDraft, options?: SubmitOptions) => void;
  isSubmitted: (dedupeKey: string) => boolean;
  refreshLeadKeys: () => Promise<void>;
}

const LeadContext = createContext<LeadContextValue | null>(null);

export function LeadProvider({ children }: { children: ReactNode }) {
  const { user, openAuth } = useAuth();
  const [submitted, setSubmitted] = useState<Set<string>>(new Set());
  const [confirmPayload, setConfirmPayload] = useState<LeadDraft | null>(null);
  const [pending, setPending] = useState<{
    payload: LeadDraft;
    options: SubmitOptions;
  } | null>(null);
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refreshLeadKeys = useCallback(async () => {
    if (!user) {
      setSubmitted(new Set());
      return;
    }
    const leads = await listProfileLeads();
    setSubmitted(new Set(leads.map((lead) => lead.dedupe_key).filter(Boolean) as string[]));
  }, [user]);

  useEffect(() => {
    if (!user) {
      setSubmitted(new Set());
      return;
    }
    listProfileLeads()
      .then((leads) => {
        setSubmitted(new Set(leads.map((lead) => lead.dedupe_key).filter(Boolean) as string[]));
      })
      .catch(() => setSubmitted(new Set()));
  }, [user]);

  const send = useCallback(
    async (payload: LeadDraft) => {
      if (!user) return false;
      setBusy(true);
      setError("");
      try {
        const { contactName, contactPhone, ...leadPayload } = payload;
        const lead = await createLead({
          ...leadPayload,
          name: contactName || user.full_name || "Клиент",
          phone: contactPhone || user.phone || "",
          consent: true,
        });
        setSubmitted((prev) => new Set(prev).add(lead.dedupe_key || payload.dedupe_key));
        setSuccess(true);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось отправить заявку");
        return false;
      } finally {
        setBusy(false);
      }
    },
    [user],
  );

  useEffect(() => {
    if (!user || !pending) return;
    const { payload, options } = pending;
    setPending(null);
    if (options.confirm) {
      setConfirmPayload(payload);
    } else {
      void send(payload);
    }
  }, [pending, send, user]);

  const submitLead = useCallback(
    (payload: LeadDraft, options: SubmitOptions = {}) => {
      if (!user) {
        setPending({ payload, options });
        openAuth("register");
        return;
      }
      if (options.confirm) {
        setConfirmPayload(payload);
        return;
      }
      void send(payload);
    },
    [openAuth, send, user],
  );

  const value = useMemo<LeadContextValue>(
    () => ({
      submitLead,
      isSubmitted: (dedupeKey) => submitted.has(dedupeKey),
      refreshLeadKeys,
    }),
    [refreshLeadKeys, submitLead, submitted],
  );

  return (
    <LeadContext.Provider value={value}>
      {children}
      <LeadModal
        confirmPayload={confirmPayload}
        busy={busy}
        error={error}
        success={success}
        onConfirm={() =>
          confirmPayload &&
          void send(confirmPayload).then((ok) => {
            if (ok) setConfirmPayload(null);
          })
        }
        onCancel={() => {
          setConfirmPayload(null);
          setError("");
        }}
        onSuccessClose={() => setSuccess(false)}
      />
    </LeadContext.Provider>
  );
}

export function useLeads() {
  const value = useContext(LeadContext);
  if (!value) throw new Error("useLeads must be used inside LeadProvider");
  return value;
}
