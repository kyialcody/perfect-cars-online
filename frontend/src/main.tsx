import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import { AuthProvider } from "./components/auth/AuthContext";
import { LeadProvider } from "./components/leads/LeadContext";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <AuthProvider>
        <LeadProvider>
          <App />
        </LeadProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
