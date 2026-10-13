import { createContext, useContext, useState, type ReactNode } from "react";

// Lets a routed page (e.g. CarPage) hand its human title to the global
// Breadcrumbs, which only knows the URL otherwise. The car breadcrumb shows the
// actual car name instead of a generic «Автомобиль».
type BreadcrumbTitle = {
  title: string | null;
  setTitle: (title: string | null) => void;
};

const BreadcrumbTitleContext = createContext<BreadcrumbTitle>({
  title: null,
  setTitle: () => {},
});

export function BreadcrumbTitleProvider({ children }: { children: ReactNode }) {
  const [title, setTitle] = useState<string | null>(null);
  return (
    <BreadcrumbTitleContext.Provider value={{ title, setTitle }}>
      {children}
    </BreadcrumbTitleContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useBreadcrumbTitle() {
  return useContext(BreadcrumbTitleContext);
}
