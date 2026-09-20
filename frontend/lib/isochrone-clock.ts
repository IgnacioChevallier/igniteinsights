/**
 * Pure helpers for the fire-progression animation.
 *
 * Everything the clock needs is already in the isochrone GeoJSON: `isochrone_converter`
 * writes `arrival_hours` on every feature, and `null` on the ones it could not time
 * (pre-`-a arrival_s` shapefiles). No backend call is involved — see
 * VISUALIZACION-ANIMADA.md parte 1.
 */

/** A feature with no usable arrival time. `coalesce` maps it to this in the map filters,
 *  which is below every real arrival hour and therefore never matches a `>= 0` clause. */
export const UNTIMED = -1;

export type IsochroneSummary = {
  /** Last hour any feature arrives. 0 when nothing is timed. */
  horizonHours: number;
  /** One isochrone step (DTDUMP expressed in hours) — the width of the active front. */
  stepHours: number;
  /** Features carrying a usable `arrival_hours`. */
  timedCount: number;
  /** Features the converter left untimed on purpose. Excluded from the animation (A5). */
  untimedCount: number;
  /** The distinct arrival hours present, ascending. What the map can actually draw. */
  levels: number[];
};

const DEFAULT_STEP_HOURS = 1;

function arrivalHours(feature: GeoJSON.Feature): number | null {
  const raw = (feature.properties ?? {})["arrival_hours"];
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

/**
 * Horizon, isochrone step and timed/untimed counts for a collection.
 *
 * The step is derived from the data rather than from DTDUMP: the namelist is not exposed
 * to the frontend, but the contour levels are exactly DTDUMP apart, so the smallest gap
 * between consecutive distinct arrival hours recovers it. Falls back to one hour when
 * there is only a single level to measure.
 */
export function summarizeIsochrones(
  collection: GeoJSON.FeatureCollection | null | undefined,
): IsochroneSummary {
  const features = collection?.features ?? [];
  const hours: number[] = [];
  let untimedCount = 0;

  for (const feature of features) {
    const h = arrivalHours(feature);
    if (h === null) untimedCount += 1;
    else hours.push(h);
  }

  if (!hours.length) {
    return {
      horizonHours: 0,
      stepHours: DEFAULT_STEP_HOURS,
      timedCount: 0,
      untimedCount,
      levels: [],
    };
  }

  const distinct = Array.from(new Set(hours)).sort((a, b) => a - b);
  let step = Infinity;
  for (let i = 1; i < distinct.length; i += 1) {
    step = Math.min(step, distinct[i] - distinct[i - 1]);
  }

  return {
    horizonHours: distinct[distinct.length - 1],
    stepHours: Number.isFinite(step) && step > 0 ? step : DEFAULT_STEP_HOURS,
    timedCount: hours.length,
    untimedCount,
    levels: distinct,
  };
}

/**
 * The largest level at or below `t`, or 0 when the cursor is before the first one.
 *
 * The map filters select `arrival_hours <= t`, and `arrival_hours` only ever takes the
 * values in `levels` — so t=3.14 and t=3.0 select exactly the same features. Passing the
 * raw 60 fps clock to the map therefore re-tessellated the whole isochrone source to draw
 * identical frames. Snapping here is what makes the map update once per level instead.
 *
 * Snapping to the level rather than to a `stepHours` grid because the two coincide only
 * when the levels are multiples of the step; if they are not, a grid would show a level
 * late.
 */
export function snapToLevel(t: number, levels: number[]): number {
  let snapped = 0;
  for (const level of levels) {
    if (level > t) break;
    snapped = level;
  }
  return snapped;
}

/** `Intl` formatting of the wall-clock instant `t` simulated hours after ignition. */
export function realTimestamp(ignitionDatetime: string | null | undefined, t: number): string | null {
  if (!ignitionDatetime) return null;
  const start = new Date(ignitionDatetime);
  if (Number.isNaN(start.getTime())) return null;
  return new Intl.DateTimeFormat("es", {
    timeZone: "UTC",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(start.getTime() + t * 3600_000));
}

/** "3,4 h" — the simulated-hour label. */
export function formatSimulatedHour(t: number): string {
  return `${t.toLocaleString("es", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} h`;
}
