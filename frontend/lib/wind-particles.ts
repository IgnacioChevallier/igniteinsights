/**
 * Windy-style wind animation over a MapLibre map.
 *
 * How Windy (and earth.nullschool.net before it, and hint.fm/wind before that) draws wind:
 * it does not draw arrows at all. It advects particles through the vector field.
 *
 *   1. Resolve the u/v field into screen space — one vector per screen position.
 *   2. Seed N particles at random screen positions, each with a random starting age.
 *   3. Every frame, move each particle along the field vector at its position and record
 *      the segment it just travelled.
 *   4. Fade the whole canvas with `globalCompositeOperation = "destination-in"` and a
 *      sub-1 alpha fill. This *multiplies* existing alpha rather than painting over it,
 *      so old segments decay into comet tails instead of being erased. This one line is
 *      what makes the effect read as flow; clearing the canvas instead gives loose dots.
 *   5. Stroke the new segments on top, in `source-over`.
 *   6. Retire a particle after MAX_AGE frames and respawn it somewhere random, otherwise
 *      the whole population drains into the field's sinks and the canvas goes empty.
 *
 * Step 1 is most of Windy's code and none of ours: a playground scenario has *uniform*
 * wind, so the field is a single screen vector, recomputed only when the map moves. What
 * is left is steps 2-6, which is the part you actually see.
 */
import type { Map as MapLibreMap } from "maplibre-gl";

export type WindField = {
  /** Where the wind blows TO, degrees clockwise from north. */
  azimuthDeg: number;
  speedMph: number;
  /** Closed lng/lat ring the wind exists inside — the scenario domain. */
  ring: [number, number][];
};

// ponytail: speed→pixels is a visual scale, not a physical one. True advection at 15 mph
// over a 12 km domain is a fraction of a pixel per frame — correct and invisible. Windy
// exaggerates for the same reason. Tune these two, not the maths.
const MIN_PX_PER_FRAME = 0.55;
const MAX_PX_PER_FRAME = 3.2;
const SPEED_SATURATES_AT_MPH = 40;

const MAX_AGE_FRAMES = 90;
/** One particle per this many square CSS pixels *of domain*, not of canvas. Seeding the
 *  whole canvas wastes most of the population outside the clip, where it is invisible. */
const PARTICLE_DENSITY = 900;

/** The density above was tuned against a playground domain occupying a corner of the map.
 *  A real run's domain fills the viewport, where the same density puts ~1400 streaks on
 *  screen and the field stops reading as wind and starts reading as rain. */
const MAX_PARTICLES = 380;
const TRAIL_DECAY = "rgba(0,0,0,0.94)";
// Slate, not blue: blue streaks over a map read as rain, which is the one thing this
// is not. Grey keeps it as motion.
const PARTICLE_COLOR = "rgba(71,85,105,0.85)";
const LINE_WIDTH = 1.2;

type Particle = { x: number; y: number; age: number };

/** Start the animation on `canvas`, over `map`. Returns a stop function. */
export function startWindParticles(
  map: MapLibreMap,
  canvas: HTMLCanvasElement,
  field: WindField,
): () => void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return () => {};

  let particles: Particle[] = [];
  let dx = 0;
  let dy = 0;
  let clip: Path2D | null = null;
  /** Screen bounding box of the domain: where particles are allowed to be born. */
  let box = { x: 0, y: 0, w: 0, h: 0 };
  let width = 0;
  let height = 0;
  let frame = 0;

  const dpr = Math.min(window.devicePixelRatio || 1, 2);

  const speedPx =
    MIN_PX_PER_FRAME +
    (MAX_PX_PER_FRAME - MIN_PX_PER_FRAME) *
      Math.min(field.speedMph / SPEED_SATURATES_AT_MPH, 1);

  /** Screen-space direction, taken from the projection rather than from the map bearing:
   *  this stays correct under rotation, pitch and the Mercator distortion for free. */
  const resolve = () => {
    const rect = map.getContainer().getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const [lng, lat] = ringCentre(field.ring);
    const rad = (field.azimuthDeg * Math.PI) / 180;
    const km = 1;
    const ahead: [number, number] = [
      lng + (Math.sin(rad) * km) / (111.32 * Math.cos((lat * Math.PI) / 180)),
      lat + (Math.cos(rad) * km) / 110.57,
    ];
    const a = map.project([lng, lat]);
    const b = map.project(ahead);
    const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    dx = ((b.x - a.x) / len) * speedPx;
    dy = ((b.y - a.y) / len) * speedPx;

    clip = new Path2D();
    let x0 = Infinity;
    let y0 = Infinity;
    let x1 = -Infinity;
    let y1 = -Infinity;
    field.ring.forEach(([rlng, rlat], i) => {
      const p = map.project([rlng, rlat]);
      if (i === 0) clip!.moveTo(p.x, p.y);
      else clip!.lineTo(p.x, p.y);
      x0 = Math.min(x0, p.x);
      y0 = Math.min(y0, p.y);
      x1 = Math.max(x1, p.x);
      y1 = Math.max(y1, p.y);
    });
    clip.closePath();
    // Clamped to the canvas: a domain panned half off-screen must not keep paying for
    // particles nobody can see.
    x0 = Math.max(x0, 0);
    y0 = Math.max(y0, 0);
    box = { x: x0, y: y0, w: Math.max(0, Math.min(x1, width) - x0), h: Math.max(0, Math.min(y1, height) - y0) };

    const wanted = Math.min(
      Math.round((box.w * box.h) / PARTICLE_DENSITY),
      MAX_PARTICLES,
    );
    particles = Array.from({ length: wanted }, () => spawn(true));
    ctx.clearRect(0, 0, width, height);
  };

  /** Particles live in the ring's screen bounding box; the canvas clip does the exact
   *  shape, so no per-particle point-in-polygon is needed. */
  const spawn = (initial: boolean): Particle => ({
    x: box.x + Math.random() * box.w,
    y: box.y + Math.random() * box.h,
    // Staggered on the first fill, so the population does not blink out in unison.
    age: initial ? Math.random() * MAX_AGE_FRAMES : 0,
  });

  const tick = () => {
    frame = requestAnimationFrame(tick);
    if (!clip) return;

    // Step 4 — decay, not erase. Unclipped: everything drawn is already inside the ring.
    ctx.globalCompositeOperation = "destination-in";
    ctx.fillStyle = TRAIL_DECAY;
    ctx.fillRect(0, 0, width, height);
    ctx.globalCompositeOperation = "source-over";

    ctx.save();
    ctx.clip(clip);
    ctx.strokeStyle = PARTICLE_COLOR;
    ctx.lineWidth = LINE_WIDTH;
    ctx.lineCap = "round";
    ctx.beginPath();
    for (const p of particles) {
      const nx = p.x + dx;
      const ny = p.y + dy;
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(nx, ny);
      p.x = nx;
      p.y = ny;
      p.age += 1;
      // Step 6 — retire and reseed, or the field drains off the edge of the screen.
      if (
        p.age > MAX_AGE_FRAMES ||
        nx < box.x || ny < box.y || nx > box.x + box.w || ny > box.y + box.h
      ) {
        Object.assign(p, spawn(false));
      }
    }
    ctx.stroke();
    ctx.restore();
  };

  resolve();
  frame = requestAnimationFrame(tick);
  map.on("move", resolve);
  map.on("resize", resolve);

  return () => {
    cancelAnimationFrame(frame);
    map.off("move", resolve);
    map.off("resize", resolve);
    ctx.clearRect(0, 0, width, height);
  };
}

function ringCentre(ring: [number, number][]): [number, number] {
  const pts = ring.slice(0, -1).length ? ring.slice(0, -1) : ring;
  const sum = pts.reduce((a, [x, y]) => [a[0] + x, a[1] + y], [0, 0]);
  return [sum[0] / pts.length, sum[1] / pts.length];
}
