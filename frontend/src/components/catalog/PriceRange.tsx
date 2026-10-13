import { useEffect, useState } from "react";
import { PRICE_MAX, PRICE_STEP } from "../../lib/catalogParams";
import { formatPrice } from "../../lib/format";
import "./price-range.css";

// Dual-handle price slider with synced number
// inputs. Local state tracks dragging; `onCommit` fires on release/blur so the
// URL (and the network request behind it) isn't rewritten on every pixel.
// `priceMax`/`priceStep` default to the car catalog bounds but can be overridden
// (e.g. the parts page uses a much smaller range).
export default function PriceRange({
  min,
  max,
  onCommit,
  priceMax = PRICE_MAX,
  priceStep = PRICE_STEP,
}: {
  min: number | undefined;
  max: number | undefined;
  onCommit: (min: number | undefined, max: number | undefined) => void;
  priceMax?: number;
  priceStep?: number;
}) {
  // Keep a value inside the slider's range. A URL like ?price_max=99999999
  // (e.g. typed into the home quick-pick) would otherwise push the fill bar's
  // right edge negative and off-screen.
  const clamp = (value: number) => Math.min(Math.max(value, 0), priceMax);
  const [lo, setLo] = useState(clamp(min ?? 0));
  const [hi, setHi] = useState(clamp(max ?? priceMax));

  // Keep local handles in sync when the URL changes elsewhere (e.g. reset).
  useEffect(() => setLo(clamp(min ?? 0)), [min]);
  useEffect(() => setHi(clamp(max ?? priceMax)), [max]);

  function commit(nextLo: number, nextHi: number) {
    onCommit(nextLo > 0 ? nextLo : undefined, nextHi < priceMax ? nextHi : undefined);
  }

  // Handles can't cross each other. Clamp so an out-of-range value can never
  // push the fill bar outside the track (left > 100% / right < 0%).
  const loPct = (clamp(lo) / priceMax) * 100;
  const hiPct = (clamp(hi) / priceMax) * 100;

  return (
    <div className="price-range">
      <div className="price-range__head">
        <span>Цена</span>
        <span className="price-range__value">
          {formatPrice(lo)} — {hi >= priceMax ? `${formatPrice(priceMax)}+` : formatPrice(hi)}
        </span>
      </div>

      <div className="price-range__track">
        <div
          className="price-range__fill"
          style={{ left: `${loPct}%`, right: `${100 - hiPct}%` }}
        />
        <input
          type="range"
          min={0}
          max={priceMax}
          step={priceStep}
          value={lo}
          aria-label="Цена от"
          // Lift the low handle above the high one past the midpoint so the two
          // thumbs stay independently grabbable when they meet near the top.
          style={{ zIndex: lo > priceMax / 2 ? 4 : 3 }}
          onChange={(e) => setLo(Math.min(Number(e.target.value), hi))}
          onMouseUp={() => commit(lo, hi)}
          onTouchEnd={() => commit(lo, hi)}
          onKeyUp={() => commit(lo, hi)}
        />
        <input
          type="range"
          min={0}
          max={priceMax}
          step={priceStep}
          value={hi}
          aria-label="Цена до"
          style={{ zIndex: 3 }}
          onChange={(e) => setHi(Math.max(Number(e.target.value), lo))}
          onMouseUp={() => commit(lo, hi)}
          onTouchEnd={() => commit(lo, hi)}
          onKeyUp={() => commit(lo, hi)}
        />
      </div>

      <div className="price-range__inputs">
        <input
          type="number"
          min={0}
          max={priceMax}
          step={priceStep}
          inputMode="numeric"
          placeholder="от 0"
          value={lo > 0 ? lo : ""}
          aria-label="Цена от, ₽"
          onChange={(e) => setLo(Number(e.target.value) || 0)}
          onBlur={() => commit(Math.min(lo, hi), hi)}
        />
        <input
          type="number"
          min={0}
          max={priceMax}
          step={priceStep}
          inputMode="numeric"
          placeholder={`до ${priceMax.toLocaleString("ru-RU")}`}
          value={hi < priceMax ? hi : ""}
          aria-label="Цена до, ₽"
          onChange={(e) => setHi(Number(e.target.value) || priceMax)}
          onBlur={() => commit(lo, Math.max(hi, lo))}
        />
      </div>
    </div>
  );
}
