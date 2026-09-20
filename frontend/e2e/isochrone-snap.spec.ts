import { expect, test } from "@playwright/test";

import { snapToLevel, summarizeIsochrones } from "../lib/isochrone-clock";

/**
 * Pure check — no page, no server.
 *
 * The map filters select `arrival_hours <= t` over a source of ~90k vertices, and
 * `arrival_hours` only ever takes the values in `levels`. Feeding it the raw 60 fps clock
 * re-tessellated the whole source to draw frames identical to the previous one. Snapping
 * is what bounds the map's work to one update per isochrone, so what has to hold is:
 * the snapped value never moves *within* a level, and never skips one.
 */

const fc = (hours: (number | null)[]): GeoJSON.FeatureCollection => ({
  type: "FeatureCollection",
  features: hours.map((h) => ({
    type: "Feature",
    properties: { arrival_hours: h },
    geometry: { type: "Point", coordinates: [0, 0] },
  })),
});

test("the snapped value only moves when the visible set does", () => {
  const levels = [1, 2, 3];

  // Anywhere inside a level, the map must be handed the same number — that identity is
  // the whole optimisation.
  expect(snapToLevel(2.0, levels)).toBe(2);
  expect(snapToLevel(2.4, levels)).toBe(2);
  expect(snapToLevel(2.99, levels)).toBe(2);
  expect(snapToLevel(3.0, levels)).toBe(3);

  // Before the first level nothing has arrived yet.
  expect(snapToLevel(0, levels)).toBe(0);
  expect(snapToLevel(0.9, levels)).toBe(0);

  // Past the horizon the final frame stays complete.
  expect(snapToLevel(99, levels)).toBe(3);

  // No levels at all: nothing to draw, and no crash.
  expect(snapToLevel(5, [])).toBe(0);
});

test("levels that are not multiples of the step still appear on time", () => {
  // The reason this snaps to the levels instead of to a `stepHours` grid: here the step
  // is 1 h but the levels sit on the half hour, so a grid would hold 0.5 back until t=1
  // and show that isochrone half an hour late.
  const summary = summarizeIsochrones(fc([0.5, 1.5, 2.5]));
  expect(summary.stepHours).toBe(1);
  expect(summary.levels).toEqual([0.5, 1.5, 2.5]);

  expect(snapToLevel(0.5, summary.levels)).toBe(0.5);
  expect(snapToLevel(0.6, summary.levels)).toBe(0.5);
});

test("untimed features never become a level", () => {
  // They render in no layer at all, so offering them to the clock would stall it on a
  // value the map cannot draw.
  const summary = summarizeIsochrones(fc([1, null, 2]));
  expect(summary.levels).toEqual([1, 2]);
  expect(summary.untimedCount).toBe(1);
});
