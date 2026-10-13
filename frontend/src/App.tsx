import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Home from "./routes/Home";
import About from "./routes/About";
import Contacts from "./routes/Contacts";
import Parts from "./routes/Parts";
import PartPage from "./routes/PartPage";
import Catalog from "./routes/Catalog";
import Select from "./routes/Select";
import Search from "./routes/Search";
import CarPage from "./routes/CarPage";
import Profile from "./routes/Profile";
import Terms from "./routes/Terms";
import Privacy from "./routes/Privacy";
import NotFound from "./routes/NotFound";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="about" element={<About />} />
        <Route path="contacts" element={<Contacts />} />
        <Route path="parts" element={<Parts />} />
        {/* «Кредит и рассрочка» is replaced by «Запчасти»; keep old links working. */}
        <Route path="credit" element={<Navigate to="/parts" replace />} />
        <Route path="catalog" element={<Catalog />} />
        <Route path="used" element={<Catalog usedOnly />} />
        <Route path="special" element={<Catalog specialOnly />} />
        <Route path="select" element={<Select />} />
        <Route path="search" element={<Search />} />
        <Route path="profile" element={<Profile />} />
        <Route path="terms" element={<Terms />} />
        <Route path="privacy" element={<Privacy />} />
        <Route path="car/:slug" element={<CarPage />} />
        <Route path="part/:slug" element={<PartPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
