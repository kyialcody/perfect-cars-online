import { useEffect } from "react";
import { useBreadcrumbTitle } from "../components/layout/BreadcrumbTitleContext";
import type { LegalDoc } from "../legal/legalContent";
import "./legal.css";

// Общий шаблон для юридических страниц (соглашение и политика). Контент —
// параметризованный текст из legalContent, зависящий от бренда/домена.
export default function LegalPage({ doc, crumbTitle }: { doc: LegalDoc; crumbTitle: string }) {
  const { setTitle } = useBreadcrumbTitle();

  useEffect(() => {
    setTitle(crumbTitle);
    return () => setTitle(null);
  }, [crumbTitle, setTitle]);

  return (
    <main className="container legal-page">
      <h1 className="legal-page__title">{doc.title}</h1>
      <p className="legal-page__updated">{doc.updated}</p>

      {doc.sections.map((section) => (
        <section className="legal-section" key={section.heading}>
          <h2 className="legal-section__heading">{section.heading}</h2>
          {section.paragraphs.map((text, i) => (
            <p className="legal-section__text" key={i}>
              {text}
            </p>
          ))}
        </section>
      ))}
    </main>
  );
}
