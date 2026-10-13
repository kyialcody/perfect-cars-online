import type { BrandOption } from "../../api/types";
import "./brand-sidebar.css";

// Brand logo sidebar (design: docs/design/home-top.png). Multi-brand by design;
// in the MVP catalog there is only Zeekr. Clicking a brand toggles the filter.
export default function BrandSidebar({
  brands,
  selected,
  onSelect,
}: {
  brands: BrandOption[];
  selected: string | undefined;
  onSelect: (slug: string | undefined) => void;
}) {
  if (brands.length === 0) return null;

  return (
    <nav className="brand-sidebar" aria-label="Бренды">
      <button
        type="button"
        className={`brand-sidebar__item${selected ? "" : " is-active"}`}
        onClick={() => onSelect(undefined)}
      >
        Все бренды
      </button>
      {brands.map((b) => (
        <button
          key={b.slug}
          type="button"
          className={`brand-sidebar__item${selected === b.slug ? " is-active" : ""}`}
          onClick={() => onSelect(selected === b.slug ? undefined : b.slug)}
          aria-pressed={selected === b.slug}
        >
          {b.logo_url && (
            <img src={b.logo_url} alt="" className="brand-sidebar__logo" loading="lazy" />
          )}
          <span className="brand-sidebar__name">{b.name}</span>
        </button>
      ))}
    </nav>
  );
}
