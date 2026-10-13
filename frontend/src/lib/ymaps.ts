// Lazily loads the Yandex Maps v3 JS API once and resolves the global `ymaps3`.
// The API is typed loosely (`any`) — we only touch a small imperative surface.

/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface Window {
    ymaps3?: any;
  }
}

let loader: Promise<any> | null = null;

export function loadYmaps(apiKey: string): Promise<any> {
  if (loader) return loader;

  loader = new Promise((resolve, reject) => {
    if (window.ymaps3) {
      window.ymaps3.ready.then(() => resolve(window.ymaps3));
      return;
    }
    const script = document.createElement("script");
    script.src = `https://api-maps.yandex.ru/v3/?apikey=${encodeURIComponent(apiKey)}&lang=ru_RU`;
    script.async = true;
    script.onload = () => {
      if (!window.ymaps3) {
        reject(new Error("ymaps3 failed to initialise"));
        return;
      }
      window.ymaps3.ready.then(() => resolve(window.ymaps3));
    };
    script.onerror = () => reject(new Error("Failed to load Yandex Maps script"));
    document.head.appendChild(script);
  });

  return loader;
}

// Route URL: opens Yandex Maps driving directions to the given point.
export function routeUrl(lat: number, lng: number): string {
  return `https://yandex.ru/maps/?rtext=~${lat},${lng}&rtt=auto`;
}
