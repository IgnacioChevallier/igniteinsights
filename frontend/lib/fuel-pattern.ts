/**
 * Vegetation textures for the schematic basemap.
 *
 * A flat block of colour says "some fuel"; a topographic map says *which* fuel, by drawing
 * the vegetation. These tiles do the same: grass tufts, shrub clusters, conifers, downed
 * logs. Ink only — no background — so they overlay the fill whose colour the server sends
 * with the geometry, and the palette keeps exactly one home (`fuels_builder`).
 *
 * The pattern id travels on the feature (`pattern: "fuel-TU"`), so the texture can never
 * disagree with the fuel model the simulation actually ran.
 */

/** Tile edge in CSS pixels. Screen-space, like a real map's vegetation hatching: the
 *  texture reads the same at every zoom instead of dissolving when you zoom out. */
const TILE = 56;

/** Sepia, the way hatching is printed on a topo sheet. Legible over every fuel colour in
 *  the palette without competing with the YlOrRd isochrones on top. */
const INK = "rgba(56,48,34,0.55)";

type Glyph = "grass" | "shrub" | "tree" | "log" | "wave";

/** `mix` is drawn one glyph per lattice cell, picked deterministically — a mix of two is
 *  how a fuel family with an understorey (TU) or a grass-shrub mosaic (GS) reads apart
 *  from a pure stand at a glance. */
const PATTERNS: Record<string, { mix: Glyph[]; cells: number; ink: string }> = {
  "fuel-GR": { mix: ["grass"], cells: 4, ink: INK },
  "fuel-GS": { mix: ["grass", "shrub"], cells: 4, ink: INK },
  "fuel-SH": { mix: ["shrub"], cells: 4, ink: INK },
  "fuel-TU": { mix: ["tree", "shrub"], cells: 3, ink: INK },
  "fuel-TL": { mix: ["tree"], cells: 3, ink: INK },
  "fuel-SB": { mix: ["log"], cells: 3, ink: INK },
  "fuel-FBFM13": { mix: ["grass", "shrub"], cells: 4, ink: INK },
  // Non-burnable ground and anything the table does not know: deliberately bare. An
  // invented texture over an unknown fuel would be a confident lie.
  "fuel-NB": { mix: [], cells: 1, ink: INK },
  "fuel-?": { mix: [], cells: 1, ink: INK },
  "fuel-water": { mix: ["wave"], cells: 3, ink: "rgba(255,255,255,0.5)" },
};

export const FUEL_PATTERN_IDS = Object.keys(PATTERNS);

/** Seeded so a reload redraws the same forest. An unseeded tile shuffles its trees on
 *  every mount, which reads as the map flickering. */
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function drawGlyph(ctx: CanvasRenderingContext2D, glyph: Glyph, cell: number, rand: () => number) {
  const h = cell * 0.5;
  switch (glyph) {
    case "grass": {
      // Blades of unequal height, splayed wide and leaning: a symmetric narrow fan reads
      // as an arrowhead (which the wind field already owns) and, drawn thick, as a blob.
      const base = cell * 0.26;
      const top = -cell * 0.34;
      const lean = (rand() - 0.5) * cell * 0.12;
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      for (const [spread, tall] of [[-1, 0.8], [-0.35, 1], [0.4, 0.9], [1, 0.65]] as const) {
        ctx.moveTo(0, base);
        ctx.quadraticCurveTo(spread * cell * 0.1, top * tall * 0.45, spread * cell * 0.3 + lean, top * tall);
      }
      ctx.stroke();
      ctx.lineWidth = 1;
      return;
    }
    case "shrub": {
      const r = cell * 0.085;
      ctx.beginPath();
      for (const [dx, dy] of [[-r, r * 0.6], [r, r * 0.6], [0, -r * 0.7]]) {
        ctx.moveTo(dx + r, dy);
        ctx.arc(dx, dy, r, 0, Math.PI * 2);
      }
      ctx.fill();
      return;
    }
    case "tree": {
      const w = cell * 0.17;
      ctx.beginPath();
      ctx.moveTo(0, -h / 2);
      ctx.lineTo(w, h * 0.28);
      ctx.lineTo(-w, h * 0.28);
      ctx.closePath();
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(0, h * 0.28);
      ctx.lineTo(0, h / 2);
      ctx.stroke();
      return;
    }
    case "log": {
      const len = cell * 0.34;
      const a = rand() * Math.PI;
      ctx.save();
      ctx.rotate(a);
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.moveTo(-len, 0);
      ctx.lineTo(len, 0);
      ctx.stroke();
      ctx.restore();
      return;
    }
    case "wave": {
      const w = cell * 0.3;
      ctx.beginPath();
      ctx.moveTo(-w, 0);
      ctx.quadraticCurveTo(-w / 2, -w * 0.45, 0, 0);
      ctx.quadraticCurveTo(w / 2, w * 0.45, w, 0);
      ctx.stroke();
    }
  }
}

/**
 * One tiling texture, as the `{width, height, data}` shape `map.addImage` takes.
 *
 * Glyphs are jittered inside their own lattice cell and never cross it, so the tile is
 * seamless without any wrap-around drawing; odd rows are offset half a cell so the
 * lattice does not read as a grid.
 */
export function fuelPatternImage(id: string, pixelRatio: number) {
  const spec = PATTERNS[id] ?? PATTERNS["fuel-?"];
  const size = Math.round(TILE * pixelRatio);
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  ctx.scale(pixelRatio, pixelRatio);
  ctx.strokeStyle = spec.ink;
  ctx.fillStyle = spec.ink;
  ctx.lineWidth = 1;
  ctx.lineCap = "round";

  const cell = TILE / spec.cells;
  const rand = rng(id.split("").reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, 7));
  for (let row = 0; row < spec.cells; row += 1) {
    for (let col = 0; col < spec.cells; col += 1) {
      if (!spec.mix.length) continue;
      const glyph = spec.mix[Math.floor(rand() * spec.mix.length)];
      // Half-cell brick offset, wrapped, so the tile still meets itself at the seam.
      const x = ((col + (row % 2) * 0.5) * cell + cell / 2 + (rand() - 0.5) * cell * 0.45) % TILE;
      const y = row * cell + cell / 2 + (rand() - 0.5) * cell * 0.45;
      ctx.save();
      ctx.translate(x, y);
      // Per-glyph scale, so the lattice reads as scattered vegetation rather than tiling.
      ctx.scale(0.88 + rand() * 0.28, 0.88 + rand() * 0.28);
      drawGlyph(ctx, glyph, cell, rand);
      ctx.restore();
    }
  }

  const image = ctx.getImageData(0, 0, size, size);
  return { width: size, height: size, data: new Uint8Array(image.data.buffer) };
}
