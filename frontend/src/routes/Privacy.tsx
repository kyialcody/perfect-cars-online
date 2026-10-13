import { getBrand } from "../lib/brand";
import { getPrivacyDoc } from "../legal/legalContent";
import LegalPage from "./LegalPage";

export default function Privacy() {
  return <LegalPage doc={getPrivacyDoc(getBrand())} crumbTitle="Политика конфиденциальности" />;
}
