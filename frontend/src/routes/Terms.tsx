import { getBrand } from "../lib/brand";
import { getTermsDoc } from "../legal/legalContent";
import LegalPage from "./LegalPage";

export default function Terms() {
  return <LegalPage doc={getTermsDoc(getBrand())} crumbTitle="Пользовательское соглашение" />;
}
