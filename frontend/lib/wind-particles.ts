/** Windy-like particle advection over a MapLibre map. */
import type { Map as MapLibreMap } from "maplibre-gl";

export type WindBand = {
  hour: number;
  u_mph: number[];
  v_mph: number[];
  speed_min_mph: number;
  speed_max_mph: number;
  speed_mph: number;
  blows_to_deg: number;
  label: string;
  direction_consistency: number;
};

export type UniformWindField = {
  kind: "uniform";
  /** Where the wind blows TO, degrees clockwise from north. */
  azimuthDeg: number;
  speedMph: number;
  ring: [number, number][];
};

export type GriddedWindField = {
  kind: "gridded";
  bounds: [west: number, south: number, east: number, north: number];
  ring: [number, number][];
  width: number;
  height: number;
  stepHours: number;
  bands: WindBand[];
};

export type WindField = UniformWindField | GriddedWindField;

export type WindSample = {
  uMph: number;
  vMph: number;
  speedMph: number;
  /** Where the wind blows TO, degrees clockwise from north. */
  azimuthDeg: number;
};

export type WindParticleController = {
  setTime: (hours: number) => void;
  setSurfaceVisible: (visible: boolean) => void;
  resize: () => void;
  stop: () => void;
};

export const WIND_SPEED_STOPS = [
  [0, "#79c7ef"],
  [5, "#54d6b0"],
  [10, "#d8dd61"],
  [20, "#f4a24b"],
  [30, "#e8596f"],
  [40, "#b87adf"],
] as const;

export const WIND_SPEED_GRADIENT = `linear-gradient(90deg, ${WIND_SPEED_STOPS.map(
  ([speed, color]) => `${color} ${(speed / 40) * 100}%`,
).join(", ")})`;

const CALM_MPH = 0.5;
const MAX_PARTICLES = 650;
const PARTICLE_DENSITY = 1900;
const MAX_TRAIL_POINTS = 18;
const MAX_TRAIL_PIXELS = 34;
const TRAIL_ALPHAS = [0.18, 0.32, 0.52, 0.78] as const;
const MIN_AGE = 58;
const MAX_AGE = 112;
const SURFACE_INTERVAL_MS = 100;

type Particle = {
  x: number;
  y: number;
  lng: number;
  lat: number;
  /** Short visual history in CSS pixels, translated with its geographic head. */
  trail: [number, number][];
  age: number;
  maxAge: number;
};

export function compassPoint(azimuthDeg: number): string {
  const points = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
  return points[Math.round((((azimuthDeg % 360) + 360) % 360) / 45) % 8];
}

export function sampleWindField(
  field: WindField,
  lng: number,
  lat: number,
  timeHours: number,
): WindSample | null {
  if (field.kind === "uniform") {
    const [west, south, east, north] = ringBounds(field.ring);
    if (lng < west || lng > east || lat < south || lat > north) return null;
    const radians = (field.azimuthDeg * Math.PI) / 180;
    return {
      uMph: Math.sin(radians) * field.speedMph,
      vMph: Math.cos(radians) * field.speedMph,
      speedMph: field.speedMph,
      azimuthDeg: ((field.azimuthDeg % 360) + 360) % 360,
    };
  }

  const [west, south, east, north] = field.bounds;
  if (lng < west || lng > east || lat < south || lat > north || !field.bands.length) {
    return null;
  }

  const x = ((lng - west) / (east - west || 1)) * (field.width - 1);
  const y = ((north - lat) / (north - south || 1)) * (field.height - 1);
  const step = field.stepHours > 0 ? field.stepHours : 1;
  const bandPosition = Math.min(
    Math.max(timeHours / step, 0),
    Math.max(field.bands.length - 1, 0),
  );
  const lowerIndex = Math.floor(bandPosition);
  const upperIndex = Math.min(lowerIndex + 1, field.bands.length - 1);
  const alpha = bandPosition - lowerIndex;
  const lower = sampleBand(field.bands[lowerIndex], field.width, field.height, x, y);
  const upper = sampleBand(field.bands[upperIndex], field.width, field.height, x, y);
  if (!lower || !upper) return null;

  const uMph = lower.u + (upper.u - lower.u) * alpha;
  const vMph = lower.v + (upper.v - lower.v) * alpha;
  const speedMph = Math.hypot(uMph, vMph);
  if (![uMph, vMph, speedMph].every(Number.isFinite)) return null;
  return {
    uMph,
    vMph,
    speedMph,
    azimuthDeg: ((Math.atan2(uMph, vMph) * 180) / Math.PI + 360) % 360,
  };
}

function sampleBand(
  band: WindBand,
  width: number,
  height: number,
  x: number,
  y: number,
): { u: number; v: number } | null {
  if (band.u_mph.length !== width * height || band.v_mph.length !== width * height) return null;
  const x0 = Math.max(0, Math.min(Math.floor(x), width - 1));
  const y0 = Math.max(0, Math.min(Math.floor(y), height - 1));
  const x1 = Math.min(x0 + 1, width - 1);
  const y1 = Math.min(y0 + 1, height - 1);
  const tx = x - x0;
  const ty = y - y0;
  const interpolate = (values: number[]) => {
    const top = values[y0 * width + x0] * (1 - tx) + values[y0 * width + x1] * tx;
    const bottom = values[y1 * width + x0] * (1 - tx) + values[y1 * width + x1] * tx;
    return top * (1 - ty) + bottom * ty;
  };
  return { u: interpolate(band.u_mph), v: interpolate(band.v_mph) };
}

/** Start particles on a DOM canvas and optionally paint a georeferenced speed canvas. */
export function startWindParticles(
  map: MapLibreMap,
  canvas: HTMLCanvasElement,
  field: WindField,
  options: {
    timeHours?: number;
    surfaceCanvas?: HTMLCanvasElement | null;
    surfaceVisible?: boolean;
    /** false keeps only the speed surface. Over 3D terrain every `unproject` is a GPU
     *  readback, and advecting particles needs one per particle per frame. */
    showParticles?: boolean;
  } = {},
): WindParticleController {
  const context = canvas.getContext("2d");
  const surfaceContext = options.surfaceCanvas?.getContext("2d") ?? null;
  if (!context) return emptyController();

  let particles: Particle[] = [];
  let clip: Path2D | null = null;
  let box = { x: 0, y: 0, w: 0, h: 0 };
  let width = 0;
  let height = 0;
  let frame = 0;
  // Fixed once the domain is first visible: zooming changes the projected size of the
  // domain, not the amount of wind information it contains.
  let particleTarget: number | null = options.showParticles === false ? 0 : null;
  let timeHours = options.timeHours ?? 0;
  let surfaceVisible = options.surfaceVisible ?? false;
  let surfaceDirty = true;
  let surfacePaintedAt = -Infinity;
  let lastFrameAt = 0;
  let stopped = false;
  const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  let reducedMotion = motionQuery.matches;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);

  const spawn = (initial: boolean): Particle => {
    let candidate = { x: box.x, y: box.y };
    for (let attempt = 0; attempt < 12; attempt += 1) {
      candidate = {
        x: box.x + Math.random() * box.w,
        y: box.y + Math.random() * box.h,
      };
      if (clip && !context.isPointInPath(clip, candidate.x, candidate.y)) continue;
      const lngLat = map.unproject([candidate.x, candidate.y]);
      const sample = sampleWindField(field, lngLat.lng, lngLat.lat, timeHours);
      if (sample && sample.speedMph >= CALM_MPH) break;
    }
    const lngLat = map.unproject([candidate.x, candidate.y]);
    const maxAge = MIN_AGE + Math.random() * (MAX_AGE - MIN_AGE);
    return {
      ...candidate,
      lng: lngLat.lng,
      lat: lngLat.lat,
      trail: [[candidate.x, candidate.y]],
      age: initial ? Math.random() * maxAge : 0,
      maxAge,
    };
  };

  const clear = () => context.clearRect(0, 0, width, height);

  const resolve = (reprojectParticles = true, clearTrails = true) => {
    const rect = map.getContainer().getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    const pixelWidth = Math.round(width * dpr);
    const pixelHeight = Math.round(height * dpr);
    const resized = canvas.width !== pixelWidth || canvas.height !== pixelHeight;
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);

    clip = new Path2D();
    let x0 = Infinity;
    let y0 = Infinity;
    let x1 = -Infinity;
    let y1 = -Infinity;
    field.ring.forEach(([lng, lat], index) => {
      const point = map.project([lng, lat]);
      if (index === 0) clip?.moveTo(point.x, point.y);
      else clip?.lineTo(point.x, point.y);
      x0 = Math.min(x0, point.x);
      y0 = Math.min(y0, point.y);
      x1 = Math.max(x1, point.x);
      y1 = Math.max(y1, point.y);
    });
    clip.closePath();
    x0 = Math.max(x0, 0);
    y0 = Math.max(y0, 0);
    box = {
      x: x0,
      y: y0,
      w: Math.max(0, Math.min(x1, width) - x0),
      h: Math.max(0, Math.min(y1, height) - y0),
    };
    if (reprojectParticles || resized) {
      for (const particle of particles) {
        const point = map.project([particle.lng, particle.lat]);
        const offsetX = point.x - particle.x;
        const offsetY = point.y - particle.y;
        for (const trailPoint of particle.trail) {
          trailPoint[0] += offsetX;
          trailPoint[1] += offsetY;
        }
        particle.x = point.x;
        particle.y = point.y;
      }
    }
    if (particleTarget === null) {
      const visibleArea = Math.min(box.w * box.h, width * height);
      // No visible domain yet (a container not laid out, or a camera still easing down from
      // 3D, where the area comes out 0 or NaN): leave it unset and retry on the next move,
      // instead of fixing the count at zero for good.
      if (visibleArea > 0) {
        particleTarget = Math.min(
          MAX_PARTICLES,
          Math.max(80, Math.round(visibleArea / PARTICLE_DENSITY)),
        );
      }
    }
    if (!particles.length && particleTarget) {
      particles = Array.from({ length: particleTarget }, () => spawn(true));
    }
    canvas.dataset.particleCount = String(particles.length);
    if (clearTrails || resized) clear();
    if (reducedMotion) drawStatic();
  };

  const projectedStep = (particle: Particle, sample: WindSample, frameScale: number) => {
    const magnitude = sample.speedMph || 1;
    const distanceKm = 1;
    const latitudeRadians = (particle.lat * Math.PI) / 180;
    const ahead = map.project([
      particle.lng +
        ((sample.uMph / magnitude) * distanceKm) /
          (111.32 * Math.max(Math.cos(latitudeRadians), 0.01)),
      particle.lat + ((sample.vMph / magnitude) * distanceKm) / 110.57,
    ]);
    const length = Math.hypot(ahead.x - particle.x, ahead.y - particle.y) || 1;
    const pixelsPerFrame = 0.35 + Math.min(sample.speedMph / 40, 1) * 2.85;
    return {
      dx: ((ahead.x - particle.x) / length) * pixelsPerFrame * frameScale,
      dy: ((ahead.y - particle.y) / length) * pixelsPerFrame * frameScale,
    };
  };

  const drawStatic = () => {
    if (!clip) return;
    clear();
    context.save();
    context.clip(clip);
    context.lineWidth = 1;
    context.lineCap = "round";
    for (const particle of particles.slice(0, 180)) {
      const point = map.project([particle.lng, particle.lat]);
      particle.x = point.x;
      particle.y = point.y;
      const sample = sampleWindField(field, particle.lng, particle.lat, timeHours);
      if (!sample || sample.speedMph < CALM_MPH) continue;
      const step = projectedStep(particle, sample, 2.4);
      context.beginPath();
      context.moveTo(particle.x - step.dx, particle.y - step.dy);
      context.lineTo(particle.x + step.dx, particle.y + step.dy);
      context.strokeStyle = colorForSpeed(sample.speedMph, 0.8);
      context.stroke();
    }
    context.restore();
  };

  const drawSurface = () => {
    const surfaceCanvas = options.surfaceCanvas;
    if (!surfaceCanvas || !surfaceContext) return;
    const surfaceWidth = field.kind === "gridded" ? field.width : 2;
    const surfaceHeight = field.kind === "gridded" ? field.height : 2;
    if (surfaceCanvas.width !== surfaceWidth || surfaceCanvas.height !== surfaceHeight) {
      surfaceCanvas.width = surfaceWidth;
      surfaceCanvas.height = surfaceHeight;
    }
    surfaceContext.clearRect(0, 0, surfaceWidth, surfaceHeight);
    if (!surfaceVisible) return;

    const image = surfaceContext.createImageData(surfaceWidth, surfaceHeight);
    const [west, south, east, north] =
      field.kind === "gridded" ? field.bounds : ringBounds(field.ring);
    for (let y = 0; y < surfaceHeight; y += 1) {
      for (let x = 0; x < surfaceWidth; x += 1) {
        const lng = west + (x / Math.max(surfaceWidth - 1, 1)) * (east - west);
        const lat = north - (y / Math.max(surfaceHeight - 1, 1)) * (north - south);
        const sample = sampleWindField(field, lng, lat, timeHours);
        const rgba = colorComponents(sample?.speedMph ?? 0);
        const offset = (y * surfaceWidth + x) * 4;
        image.data[offset] = rgba[0];
        image.data[offset + 1] = rgba[1];
        image.data[offset + 2] = rgba[2];
        image.data[offset + 3] = sample && sample.speedMph >= CALM_MPH ? 255 : 0;
      }
    }
    surfaceContext.putImageData(image, 0, 0);
  };

  const appendTrail = (
    paths: Path2D[],
    trail: [number, number][],
    targetPixels: number,
  ) => {
    if (trail.length < 2) return;
    const visible = [{ x: trail.at(-1)![0], y: trail.at(-1)![1] }];
    let distance = 0;

    for (let index = trail.length - 2; index >= 0; index -= 1) {
      const older = { x: trail[index][0], y: trail[index][1] };
      const newer = visible[0];
      const segment = Math.hypot(newer.x - older.x, newer.y - older.y);
      if (distance + segment > targetPixels) {
        const remaining = targetPixels - distance;
        if (remaining > 0 && segment > 0) {
          const ratio = remaining / segment;
          visible.unshift({
            x: newer.x + (older.x - newer.x) * ratio,
            y: newer.y + (older.y - newer.y) * ratio,
          });
        }
        break;
      }
      visible.unshift(older);
      distance += segment;
    }

    for (let index = 1; index < visible.length; index += 1) {
      const progress = index / Math.max(visible.length - 1, 1);
      const alphaIndex = Math.min(
        TRAIL_ALPHAS.length - 1,
        Math.floor(progress * TRAIL_ALPHAS.length),
      );
      paths[alphaIndex].moveTo(visible[index - 1].x, visible[index - 1].y);
      paths[alphaIndex].lineTo(visible[index].x, visible[index].y);
    }
  };

  const tick = (timestamp: number) => {
    if (stopped) return;
    frame = requestAnimationFrame(tick);
    if (surfaceDirty && timestamp - surfacePaintedAt >= SURFACE_INTERVAL_MS) {
      drawSurface();
      surfacePaintedAt = timestamp;
      surfaceDirty = false;
    }
    if (!clip || reducedMotion) return;

    const frameScale = lastFrameAt ? Math.min((timestamp - lastFrameAt) / 16.667, 2.5) : 1;
    lastFrameAt = timestamp;
    clear();

    const paths = WIND_SPEED_STOPS.map(() => TRAIL_ALPHAS.map(() => new Path2D()));
    context.save();
    context.clip(clip);
    for (const particle of particles) {
      // The head lives in geographic space. Move its short screen-space history by the
      // same camera delta, which anchors the streak to the map without scaling its visual
      // length or performing thousands of historical projections on every frame.
      const point = map.project([particle.lng, particle.lat]);
      const cameraOffsetX = point.x - particle.x;
      const cameraOffsetY = point.y - particle.y;
      for (const trailPoint of particle.trail) {
        trailPoint[0] += cameraOffsetX;
        trailPoint[1] += cameraOffsetY;
      }
      particle.x = point.x;
      particle.y = point.y;
      const sample = sampleWindField(field, particle.lng, particle.lat, timeHours);
      if (!sample || sample.speedMph < CALM_MPH) {
        Object.assign(particle, spawn(false));
        continue;
      }
      const step = projectedStep(particle, sample, frameScale);
      const nextX = particle.x + step.dx;
      const nextY = particle.y + step.dy;
      particle.x = nextX;
      particle.y = nextY;
      const nextLngLat = map.unproject([nextX, nextY]);
      particle.lng = nextLngLat.lng;
      particle.lat = nextLngLat.lat;
      particle.trail.push([nextX, nextY]);
      if (particle.trail.length > MAX_TRAIL_POINTS) particle.trail.shift();
      particle.age += frameScale;
      if (
        particle.age > particle.maxAge ||
        nextX < box.x ||
        nextY < box.y ||
        nextX > box.x + box.w ||
        nextY > box.y + box.h
      ) {
        Object.assign(particle, spawn(false));
        continue;
      }
      const targetPixels = Math.min(
        MAX_TRAIL_PIXELS,
        (0.35 + Math.min(sample.speedMph / 40, 1) * 2.85) * (MAX_TRAIL_POINTS - 1),
      );
      appendTrail(paths[colorBucket(sample.speedMph)], particle.trail, targetPixels);
    }
    context.lineWidth = 1;
    context.lineCap = "round";
    paths.forEach((alphaPaths, colorIndex) => {
      alphaPaths.forEach((path, alphaIndex) => {
        context.strokeStyle = hexToRgba(
          WIND_SPEED_STOPS[colorIndex][1],
          TRAIL_ALPHAS[alphaIndex],
        );
        context.stroke(path);
      });
    });
    context.restore();
  };

  const onMove = () => {
    // Only projection geometry changes here. The animation loop continues and redraws
    // every geographic trail against the new camera on its next frame.
    resolve(false, false);
  };
  const onResize = () => resolve(true, true);
  const onMotionChange = (event: MediaQueryListEvent) => {
    reducedMotion = event.matches;
    lastFrameAt = 0;
    if (reducedMotion) drawStatic();
    else clear();
  };

  resolve();
  drawSurface();
  frame = requestAnimationFrame(tick);
  map.on("move", onMove);
  map.on("resize", onResize);
  motionQuery.addEventListener("change", onMotionChange);

  const stop = () => {
    stopped = true;
    cancelAnimationFrame(frame);
    map.off("move", onMove);
    map.off("resize", onResize);
    motionQuery.removeEventListener("change", onMotionChange);
    clear();
    if (options.surfaceCanvas && surfaceContext) {
      surfaceContext.clearRect(0, 0, options.surfaceCanvas.width, options.surfaceCanvas.height);
    }
  };

  return {
    setTime: (hours) => {
      timeHours = hours;
      surfaceDirty = true;
      if (reducedMotion) drawStatic();
    },
    setSurfaceVisible: (visible) => {
      surfaceVisible = visible;
      surfaceDirty = true;
      drawSurface();
    },
    resize: resolve,
    stop,
  };
}

function ringBounds(ring: [number, number][]): [number, number, number, number] {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  for (const [lng, lat] of ring) {
    west = Math.min(west, lng);
    south = Math.min(south, lat);
    east = Math.max(east, lng);
    north = Math.max(north, lat);
  }
  return [west, south, east, north];
}

function colorBucket(speedMph: number): number {
  for (let index = WIND_SPEED_STOPS.length - 1; index >= 0; index -= 1) {
    if (speedMph >= WIND_SPEED_STOPS[index][0]) return index;
  }
  return 0;
}

function colorComponents(speedMph: number): [number, number, number] {
  const upperIndex = WIND_SPEED_STOPS.findIndex(([speed]) => speed >= speedMph);
  if (upperIndex <= 0) return hexComponents(WIND_SPEED_STOPS[0][1]);
  if (upperIndex === -1) return hexComponents(WIND_SPEED_STOPS.at(-1)![1]);
  const [lowerSpeed, lowerColor] = WIND_SPEED_STOPS[upperIndex - 1];
  const [upperSpeed, upperColor] = WIND_SPEED_STOPS[upperIndex];
  const alpha = (speedMph - lowerSpeed) / (upperSpeed - lowerSpeed || 1);
  const lower = hexComponents(lowerColor);
  const upper = hexComponents(upperColor);
  return lower.map((value, index) => Math.round(value + (upper[index] - value) * alpha)) as [
    number,
    number,
    number,
  ];
}

function hexComponents(hex: string): [number, number, number] {
  return [
    Number.parseInt(hex.slice(1, 3), 16),
    Number.parseInt(hex.slice(3, 5), 16),
    Number.parseInt(hex.slice(5, 7), 16),
  ];
}

function hexToRgba(hex: string, alpha: number): string {
  const [red, green, blue] = hexComponents(hex);
  return `rgba(${red},${green},${blue},${alpha})`;
}

function colorForSpeed(speedMph: number, alpha: number): string {
  const [red, green, blue] = colorComponents(speedMph);
  return `rgba(${red},${green},${blue},${alpha})`;
}

function emptyController(): WindParticleController {
  return {
    setTime: () => {},
    setSurfaceVisible: () => {},
    resize: () => {},
    stop: () => {},
  };
}
