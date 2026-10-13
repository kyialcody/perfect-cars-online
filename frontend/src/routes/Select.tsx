import CollectionsGrid from "../components/CollectionsGrid";
import "./select.css";

// «Подбор авто» page (nav → /select): all admin-managed collections as a
// paginated grid, full width.
export default function Select() {
  return (
    <div className="container select-page">
      <CollectionsGrid />
    </div>
  );
}
