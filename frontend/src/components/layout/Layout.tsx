import { Outlet } from "react-router-dom";
import Breadcrumbs from "./Breadcrumbs";
import { BreadcrumbTitleProvider } from "./BreadcrumbTitleContext";
import Header from "./Header";
import Footer from "./Footer";
import CookieConsent from "../CookieConsent";
import "./layout.css";

// App shell: fixed Header/Footer slots around the routed page.
// Header and Footer are placeholders here — built out in issue #13.
export default function Layout() {
  return (
    <div className="app-shell">
      <Header />
      <BreadcrumbTitleProvider>
        <Breadcrumbs />
        <main className="app-main">
          <Outlet />
        </main>
      </BreadcrumbTitleProvider>
      <Footer />
      <CookieConsent />
    </div>
  );
}
