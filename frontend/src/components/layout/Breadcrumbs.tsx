import { Link, useLocation } from "react-router-dom";
import { useBreadcrumbTitle } from "./BreadcrumbTitleContext";
import { getBreadcrumbs } from "./breadcrumbItems";
import "./breadcrumbs.css";

export default function Breadcrumbs() {
  const location = useLocation();
  const { title } = useBreadcrumbTitle();
  const breadcrumbs = getBreadcrumbs(location, title);

  if (breadcrumbs.length <= 1) return null;

  return (
    <nav className="breadcrumbs" aria-label="Хлебные крошки">
      <div className="container breadcrumbs__inner">
        {breadcrumbs.map((crumb, index) => (
          <span className="breadcrumbs__item" key={`${crumb.label}-${index}`}>
            {crumb.to && index < breadcrumbs.length - 1 ? (
              <Link to={crumb.to}>{crumb.label}</Link>
            ) : (
              crumb.label
            )}
          </span>
        ))}
      </div>
    </nav>
  );
}
