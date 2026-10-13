import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError, getStoredTokens } from "../../api/client";
import {
  login,
  loginAfterRegister,
  logout as clearAuth,
  me,
  register,
  type LoginPayload,
  type RegisterPayload,
  type UserOut,
} from "../../api/auth";
import AuthModal from "./AuthModal";

type PendingAction = () => void | Promise<void>;

interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  openAuth: (mode?: "login" | "register") => void;
  requireAuth: (action: PendingAction) => void;
  signIn: (payload: LoginPayload) => Promise<void>;
  signUp: (payload: RegisterPayload) => Promise<void>;
  signOut: () => void;
  setUser: (user: UserOut) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"login" | "register" | null>(null);
  const pending = useRef<PendingAction | null>(null);

  useEffect(() => {
    if (!getStoredTokens()) {
      setLoading(false);
      return;
    }
    me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const runPending = useCallback(async () => {
    const action = pending.current;
    pending.current = null;
    if (action) await action();
  }, []);

  const openAuth = useCallback((mode: "login" | "register" = "login") => {
    setModal(mode);
  }, []);

  const requireAuth = useCallback(
    (action: PendingAction) => {
      if (user) {
        void action();
        return;
      }
      pending.current = action;
      setModal("register");
    },
    [user],
  );

  const signIn = useCallback(
    async (payload: LoginPayload) => {
      const next = await login(payload);
      setUser(next);
      setModal(null);
      await runPending();
    },
    [runPending],
  );

  const signUp = useCallback(
    async (payload: RegisterPayload) => {
      try {
        await register(payload);
      } catch (error) {
        if (error instanceof ApiError && error.status === 451) {
          throw new Error("По законодательству РФ нельзя зарегистрироваться через @gmail.com");
        }
        throw error;
      }
      const next = await loginAfterRegister(payload.email, payload.password);
      setUser(next);
      setModal(null);
      await runPending();
    },
    [runPending],
  );

  const signOut = useCallback(() => {
    clearAuth();
    setUser(null);
    pending.current = null;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      openAuth,
      requireAuth,
      signIn,
      signUp,
      signOut,
      setUser,
    }),
    [loading, openAuth, requireAuth, signIn, signOut, signUp, user],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      <AuthModal mode={modal} onClose={() => setModal(null)} onLogin={signIn} onRegister={signUp} />
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
