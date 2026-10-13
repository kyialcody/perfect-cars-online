import { useEffect, useRef, useState } from "react";
import { Clock, MapPin, Phone } from "lucide-react";
import type { DealerLocation } from "../api/types";
import { loadYmaps, routeUrl } from "../lib/ymaps";
import "./yandex-map.css";

const API_KEY = import.meta.env.VITE_YANDEX_MAPS_API_KEY ?? "";

// Bounding box around all pins, padded so markers aren't on the edge.
// ymaps3 bounds = [[minLng, maxLat], [maxLng, minLat]] (NW corner, SE corner).
function boundsOf(locations: DealerLocation[]): [[number, number], [number, number]] {
  const lngs = locations.map((l) => l.lng);
  const lats = locations.map((l) => l.lat);
  let minLng = Math.min(...lngs);
  let maxLng = Math.max(...lngs);
  let minLat = Math.min(...lats);
  let maxLat = Math.max(...lats);
  const padLng = (maxLng - minLng) * 0.25 || 0.01;
  const padLat = (maxLat - minLat) * 0.25 || 0.01;
  minLng -= padLng;
  maxLng += padLng;
  minLat -= padLat;
  maxLat += padLat;
  return [
    [minLng, maxLat],
    [maxLng, minLat],
  ];
}

export default function YandexMap({
  locations,
  onUnavailable,
}: {
  locations: DealerLocation[];
  onUnavailable?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [selected, setSelected] = useState<DealerLocation | null>(locations[0] ?? null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!API_KEY || locations.length === 0) {
      setFailed(true);
      onUnavailable?.();
      return;
    }

    // ymaps3 map instance — loosely typed (imperative API surface).
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let map: any = null;
    let cancelled = false;

    loadYmaps(API_KEY)
      .then((ymaps3) => {
        if (cancelled || !ref.current) return;
        const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker } = ymaps3;

        // One pin → center + close zoom. Multiple → fit bounds so all are
        // visible; the user zooms in to the one they want.
        map = new YMap(ref.current, {
          location:
            locations.length > 1
              ? { bounds: boundsOf(locations) }
              : { center: [locations[0].lng, locations[0].lat], zoom: 15 },
        });
        map.addChild(new YMapDefaultSchemeLayer());
        map.addChild(new YMapDefaultFeaturesLayer());

        for (const loc of locations) {
          const el = document.createElement("button");
          el.type = "button";
          el.className = "ymap-pin";
          el.setAttribute("aria-label", loc.name);
          el.addEventListener("click", () => setSelected(loc));
          map!.addChild(new YMapMarker({ coordinates: [loc.lng, loc.lat] }, el));
        }
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        onUnavailable?.();
      });

    return () => {
      cancelled = true;
      map?.destroy();
    };
    // onUnavailable is a stable callback from the parent; locations drives the map.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locations]);

  // No key or load error → let the parent render its static fallback.
  if (failed) return null;

  return (
    <div className="ymap">
      <div className="ymap__canvas" ref={ref} />
      {selected && (
        <div className="ymap__card">
          {selected.phone && (
            <div>
              <Phone size={16} aria-hidden="true" />
              <span>{selected.phone}</span>
            </div>
          )}
          {selected.hours && (
            <div>
              <Clock size={16} aria-hidden="true" />
              <span>{selected.hours}</span>
            </div>
          )}
          <div>
            <MapPin size={16} aria-hidden="true" />
            <span>{selected.address}</span>
          </div>
          <a
            className="btn btn--primary"
            href={routeUrl(selected.lat, selected.lng)}
            target="_blank"
            rel="noopener noreferrer"
          >
            Как до нас добраться
          </a>
        </div>
      )}
    </div>
  );
}
