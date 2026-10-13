import type { Location } from "react-router-dom";

export type BreadcrumbItem = {
  to?: string;
  label: string;
};

export function getBreadcrumbs(location: Location, carTitle?: string | null): BreadcrumbItem[] {
  const search = new URLSearchParams(location.search);
  const crumbs: BreadcrumbItem[] = [{ to: "/", label: "Главная" }];

  if (location.pathname === "/") {
    return crumbs;
  }

  if (location.pathname === "/catalog") {
    crumbs.push({
      label: search.get("condition") === "used" ? "Авто с пробегом" : "Каталог авто",
    });
  } else if (location.pathname === "/used") {
    crumbs.push({ label: "Авто с пробегом" });
  } else if (location.pathname.startsWith("/car/")) {
    // The card passes the source tab in navigation state, so the parent crumb
    // links back to the right list (new / used / special); the leaf is the
    // real car name.
    const from = (location.state as { catalogCondition?: string } | null)?.catalogCondition;
    const parent =
      from === "used"
        ? { to: "/used", label: "Авто с пробегом" }
        : from === "special"
          ? { to: "/special", label: "Спецпредложения" }
          : { to: "/catalog", label: "Каталог авто" };
    crumbs.push(parent, { label: carTitle || "Автомобиль" });
  } else if (location.pathname.startsWith("/part/")) {
    crumbs.push({ to: "/parts", label: "Запчасти" }, { label: carTitle || "Запчасть" });
  } else if (location.pathname === "/parts") {
    crumbs.push({ label: "Запчасти" });
  } else if (location.pathname === "/special") {
    crumbs.push({ label: "Спецпредложения" });
  } else if (location.pathname === "/select") {
    crumbs.push({ label: "Подбор авто" });
  } else if (location.pathname === "/about") {
    crumbs.push({ label: "О компании" });
  } else if (location.pathname === "/contacts") {
    crumbs.push({ label: "Контакты" });
  } else if (location.pathname === "/terms") {
    crumbs.push({ label: carTitle || "Пользовательское соглашение" });
  } else if (location.pathname === "/privacy") {
    crumbs.push({ label: carTitle || "Политика конфиденциальности" });
  }

  return crumbs;
}
