import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="container" style={{ paddingBlock: "var(--space-12)" }}>
      <h1 style={{ fontSize: 32 }}>404</h1>
      <p style={{ color: "var(--color-gray)" }}>Страница не найдена.</p>
      <Link to="/" style={{ color: "var(--color-red)" }}>
        На главную
      </Link>
    </div>
  );
}
