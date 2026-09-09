"use client";

import { useEffect, useMemo, useState } from "react";
import { FireMap, WATER_COLOR, WIND_COLOR } from "@/components/fire-map";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { WindField } from "@/lib/wind-particles";

// GET /api/v1/playground/presets
type Scenario = Record<string, unknown> & { name: string; description: string };

type Preset = {
  id: string;
  order: number;
  group: string;
  changes_from: string | null;
  expectation: string;
  scenario: Scenario;
};

type Metrics = {
  cell_size_m: number;
  burned_cells: number;
  reached_domain_edge: boolean;
  final: {
    burned_ha: number;
    max_distance_m: number;
    head_ros_m_per_h: number;
    head_ros_class: string;
    head_direction_deg: number | null;
    aspect_ratio: number | null;
  };
  hourly: { hour: number; burned_ha: number; max_distance_m: number }[];
};

type FuelModel = {
  code: number;
  name: string;
  fuel_type: string;
  fuel_type_label: string;
  color: string;
  label: string;
};

// The ground the scenario runs on, as a scenario patch applied on top of the preset.
// Applied last and owning every field it touches, so what the thumbnail shows is what the
// run gets — a preset's own slope included. Slope is 30°/aspect 0 to match the
// "Topografía" presets: one number for the same idea, not two.
const TERRAINS = [
  {
    id: "uniform",
    label: "Uniforme",
    hint: "Una sola clase de combustible, terreno plano. El control.",
    patch: { terrain: "uniform", slope_deg: 0, aspect_deg: 0 },
  },
  {
    id: "lake",
    label: "Con lago",
    hint: "Un parche no combustible (FBFM 98) en el camino del fuego: qué le hace una barrera al frente.",
    patch: { terrain: "lake", slope_deg: 0, aspect_deg: 0 },
  },
  {
    id: "slope",
    label: "En ladera",
    hint: "Pendiente uniforme de 30° que baja hacia el norte. El fuego corre cuesta arriba.",
    patch: { terrain: "uniform", slope_deg: 30, aspect_deg: 0 },
  },
] as const;

type TerrainId = (typeof TERRAINS)[number]["id"];

// Same values the synthetic basemap paints with, so the thumbnail is a miniature of the
// map and not an illustration of it. The slab green stands for "bosque" whatever fuel
// model the preset carries: the picker chooses the ground, not the fuel.
const SCHEMATIC_BG = "#eceae4";
const SCHEMATIC_SLAB = "#4a7a3a";

type Slot = {
  preset: Preset | null;
  isochrones: GeoJSON.FeatureCollection | null;
  metrics: Metrics | null;
  /** The scenario drawn as itself: uniform fuel slab, ignition disc, forcing vectors. */
  mapLayers: GeoJSON.FeatureCollection | null;
  fuelModel: FuelModel | null;
  status: "idle" | "running" | "error";
  error?: string;
};

const EMPTY_SLOT: Slot = {
  preset: null, isochrones: null, metrics: null,
  mapLayers: null, fuelModel: null, status: "idle",
};

const num = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined ? "—" : v.toLocaleString("es", { maximumFractionDigits: digits });

async function runScenario(scenario: Scenario) {
  const runRes = await fetch("/api/playground/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  const runEnv = await runRes.json();
  if (!runRes.ok || !runEnv?.data?.simulation_id) {
    throw new Error(runEnv?.detail ?? runEnv?.error?.message ?? "La simulación falló");
  }
  const id: string = runEnv.data.simulation_id;

  const [isoEnv, metEnv] = await Promise.all([
    fetch(`/api/simulations/${id}/isochrones`, { cache: "no-store" }).then((r) => r.json()),
    fetch(`/api/playground/${id}/metrics`, { cache: "no-store" }).then((r) => r.json()),
  ]);
  return {
    isochrones: (isoEnv?.data ?? null) as GeoJSON.FeatureCollection | null,
    metrics: (metEnv?.data ?? null) as Metrics | null,
    mapLayers: (runEnv.data.map_layers ?? null) as GeoJSON.FeatureCollection | null,
    fuelModel: (runEnv.data.fuel_model ?? null) as FuelModel | null,
  };
}

/** The scenario's own geometry, without running it. Pure and fast: the panel calls it the
 *  moment a scenario or a terrain is picked, so the map never waits on ELMFIRE. */
async function previewScenario(scenario: Scenario) {
  const res = await fetch("/api/playground/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
    cache: "no-store",
  });
  const env = await res.json();
  if (!res.ok || !env?.data) throw new Error(env?.detail ?? "No se pudo dibujar el escenario");
  return env.data as { map_layers: GeoJSON.FeatureCollection; fuel_model: FuelModel };
}

export function PlaygroundPanel() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [slots, setSlots] = useState<[Slot, Slot]>([EMPTY_SLOT, EMPTY_SLOT]);
  const [terrain, setTerrain] = useState<TerrainId>("uniform");

  useEffect(() => {
    fetch("/api/playground/presets", { cache: "no-store" })
      .then(async (res) => {
        const env = await res.json();
        if (!res.ok || !env.data) throw new Error(env.detail ?? "Sin datos");
        setPresets(env.data.presets as Preset[]);
      })
      .catch((e: Error) => setLoadError(e.message));
  }, []);

  const updateSlot = (i: 0 | 1, fn: (s: Slot) => Slot) =>
    setSlots((prev) => (i === 0 ? [fn(prev[0]), prev[1]] : [prev[0], fn(prev[1])]));

  const scenarioOn = (preset: Preset, id: TerrainId) => ({
    ...preset.scenario,
    ...TERRAINS.find((t) => t.id === id)!.patch,
  });

  /** Draw a scenario into a slot. A failed preview only costs the early picture — the run
   *  response carries the same layers — so it is swallowed rather than shown as an error. */
  const draw = (preset: Preset, id: TerrainId, slotIndex: 0 | 1) =>
    previewScenario(scenarioOn(preset, id))
      .then((p) =>
        updateSlot(slotIndex, (s) => ({ ...s, mapLayers: p.map_layers, fuelModel: p.fuel_model })),
      )
      .catch(() => {});

  const chooseTerrain = (id: TerrainId) => {
    setTerrain(id);
    // Whatever is on screen was produced on the old ground. Keep the scenarios, drop the
    // isochrones and the metrics — leaving them would invite reading a lake-less result
    // as if it had run with the lake — and redraw each map on the new terrain.
    ([0, 1] as const).forEach((i) => {
      const preset = slots[i].preset;
      updateSlot(i, (s) => ({ ...s, isochrones: null, metrics: null, status: "idle", error: undefined }));
      if (preset) draw(preset, id, i);
    });
  };

  const run = async (preset: Preset, slotIndex: 0 | 1) => {
    updateSlot(slotIndex, () => ({
      preset, isochrones: null, metrics: null,
      mapLayers: null, fuelModel: null, status: "running",
    }));
    draw(preset, terrain, slotIndex);
    try {
      const result = await runScenario(scenarioOn(preset, terrain));
      updateSlot(slotIndex, () => ({ preset, ...result, status: "idle" }));
    } catch (e) {
      updateSlot(slotIndex, (s) => ({ ...s, status: "error", error: (e as Error).message }));
    }
  };

  const groups = Array.from(new Set(presets.map((p) => p.group)));

  // Memoised: a fresh object every render would restart the particle animation and wipe
  // its trails each time anything in the panel changes.
  const windFields = useMemo(
    () => slots.map((slot) => toWindField(slot.mapLayers)) as [WindField | null, WindField | null],
    [slots],
  );

  return (
    <div className="flex h-full">
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="border-b bg-amber-50 px-3 py-1.5 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-100">
          Dominios <strong>sintéticos</strong>: viento y combustible uniformes sobre el
          terreno que elijas. Se dibujan sobre el AOI sólo para dar escala — no son una
          predicción para ese lugar.
        </div>
        <div className="grid min-h-0 flex-1 grid-cols-2 divide-x">
          {slots.map((slot, i) => (
            <div key={i} className="relative min-h-0">
              <FireMap
                isochrones={slot.isochrones}
                fitTo={slot.mapLayers ?? slot.isochrones}
                syntheticLayers={slot.mapLayers}
                windField={windFields[i]}
                initialBasemap="synthetic"
              />
              {slot.fuelModel && (
                // Stacked above FireMap's own legend, which also sits at bottom-left —
                // at the same offset this box covered the isochrone key entirely.
                <div className="pointer-events-none absolute bottom-24 left-2 z-10 rounded-md bg-background/90 px-2 py-1 text-[11px] shadow">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-3 w-3 shrink-0 rounded-sm border"
                      style={{ backgroundColor: slot.fuelModel.color }}
                    />
                    <span>{slot.fuelModel.label}</span>
                  </div>
                  {/* Each key only appears when its arrow is on the map: a scenario with
                      no slope drew no slope arrow, and a legend for it is a lie. */}
                  <div className="mt-0.5 flex items-center gap-3 text-muted-foreground">
                    {slot.mapLayers?.features?.some((f) => f.properties?.kind === "water") && (
                      <span className="flex items-center gap-1">
                        <span
                          className="inline-block h-3 w-3 shrink-0 rounded-sm border"
                          style={{ backgroundColor: WATER_COLOR }}
                        />
                        lago (no combustible)
                      </span>
                    )}
                    {(["wind", "slope"] as const)
                      .map((kind) => [
                        kind,
                        slot.mapLayers?.features?.find((f) => f.properties?.kind === kind),
                      ] as const)
                      .filter(([, feature]) => feature)
                      .map(([kind, feature]) => (
                        <span key={kind} className="flex items-center gap-1">
                          <span
                            className="inline-block h-0.5 w-4"
                            style={{ backgroundColor: kind === "wind" ? WIND_COLOR : "#57534e" }}
                          />
                          {/* The server's own label. For wind it names the compass point
                              ("hacia el SO"): a 45° rotation of a burn scar elongated 1.1×
                              is invisible in a still, and the animation says nothing in a
                              screenshot. The words are what make the two runs tell apart. */}
                          {String(feature!.properties?.label ?? kind)}
                        </span>
                      ))}
                  </div>
                </div>
              )}
              {/* Below the basemap switcher, which also lives at top-left: at the same
                  offset a long scenario name covered "Calles / Satélite / Esquemático"
                  entirely. */}
              <div className="pointer-events-none absolute left-2 top-11 z-10 max-w-[calc(100%-1rem)] rounded-md bg-background/90 px-2 py-1 text-xs shadow">
                <span className="font-semibold">{i === 0 ? "A" : "B"}</span>
                {" · "}
                {slot.status === "running"
                  ? "corriendo…"
                  : slot.status === "error"
                    ? `error: ${slot.error}`
                    : (slot.preset?.scenario.name ?? "sin escenario")}
              </div>
            </div>
          ))}
        </div>
      </div>

      <aside className="flex w-96 shrink-0 flex-col gap-3 overflow-auto border-l bg-background p-3">
        <div>
          <h2 className="text-sm font-medium">Playground de sensibilidad</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Cada escenario cambia <strong>un solo factor</strong> respecto del anterior.
            Cargá dos en A y B para que la diferencia sea atribuible a ese factor.
          </p>
        </div>

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Terreno
          </h3>
          <div className="mt-1.5 grid grid-cols-3 gap-1.5">
            {TERRAINS.map((t) => (
              <button
                key={t.id}
                onClick={() => chooseTerrain(t.id)}
                title={t.hint}
                aria-pressed={terrain === t.id}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-md border p-1.5 transition-colors",
                  "hover:bg-muted",
                  terrain === t.id && "border-primary ring-1 ring-primary",
                )}
              >
                <TerrainThumb id={t.id} />
                <span className="text-[11px] font-medium">{t.label}</span>
              </button>
            ))}
          </div>
          <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
            {TERRAINS.find((t) => t.id === terrain)!.hint}
          </p>
        </section>

        {loadError && <p className="text-xs text-destructive">{loadError}</p>}

        <Comparison a={slots[0]} b={slots[1]} />

        <Separator />

        {groups.map((group) => (
          <section key={group} className="flex flex-col gap-1.5">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {group}
            </h3>
            {presets
              .filter((p) => p.group === group)
              .sort((x, y) => x.order - y.order)
              .map((preset) => (
                <div key={preset.id} className="rounded-md border p-2">
                  <p className="text-xs font-medium">{preset.scenario.name}</p>
                  <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                    {preset.expectation}
                  </p>
                  <div className="mt-1.5 flex gap-1.5">
                    {([0, 1] as const).map((i) => (
                      <button
                        key={i}
                        onClick={() => run(preset, i)}
                        disabled={slots[i].status === "running"}
                        className={cn(
                          "rounded border px-2 py-0.5 text-[11px] font-medium transition-colors",
                          "hover:bg-muted disabled:opacity-50",
                          slots[i].preset?.id === preset.id && "bg-primary text-primary-foreground",
                        )}
                      >
                        Correr en {i === 0 ? "A" : "B"}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
          </section>
        ))}
      </aside>
    </div>
  );
}

/** A miniature of the schematic map, not an illustration of it: same background, same
 *  slab opacity, same red ignition disc, same blue lake. Clicking the picture is the
 *  whole point — you pick the ground by recognising it, not by reading a dropdown. */
function TerrainThumb({ id }: { id: TerrainId }) {
  return (
    <svg viewBox="0 0 48 34" className="h-[34px] w-full" aria-hidden="true">
      <rect width="48" height="34" fill={SCHEMATIC_BG} />
      <rect
        x="3" y="3" width="42" height="28"
        fill={SCHEMATIC_SLAB} fillOpacity="0.45" stroke="#57534e" strokeWidth="1"
      />
      {id === "slope" && (
        <g stroke="#57534e" fill="none">
          {[11, 17, 23].map((y) => (
            <line key={y} x1="4" y1={y} x2="44" y2={y} strokeWidth="0.5" strokeOpacity="0.5" />
          ))}
          {/* Downslope, matching the map's own arrow convention. */}
          <path d="M37 9 L37 26 M37 26 L34.8 22.8 M37 26 L39.2 22.8" strokeWidth="1.2" />
        </g>
      )}
      {id === "lake" && <circle cx="32" cy="17" r="7" fill={WATER_COLOR} />}
      <circle cx="17" cy="17" r="2.6" fill="#b30000" />
    </svg>
  );
}

/** The scenario's wind, as the animation wants it: where it blows TO, and the slab it
 *  blows over. Both already travel with the map layers the server built. */
function toWindField(layers: GeoJSON.FeatureCollection | null): WindField | null {
  const wind = layers?.features?.find((f) => f.properties?.kind === "wind");
  const domain = layers?.features?.find((f) => f.properties?.kind === "domain");
  if (!wind || domain?.geometry?.type !== "Polygon") return null;
  return {
    azimuthDeg: Number(wind.properties?.azimuth_deg ?? 0),
    speedMph: Number(wind.properties?.speed_mph ?? 0),
    ring: domain.geometry.coordinates[0] as [number, number][],
  };
}

function Comparison({ a, b }: { a: Slot; b: Slot }) {
  if (!a.metrics && !b.metrics) return null;

  const rows: [string, (m: Metrics) => string][] = [
    ["Área quemada", (m) => `${num(m.final.burned_ha, 0)} ha`],
    ["Distancia máx.", (m) => `${num(m.final.max_distance_m, 0)} m`],
    ["ROS de cabeza", (m) => `${num(m.final.head_ros_m_per_h, 0)} m/h`],
    ["Clase (Scott & Burgan)", (m) => m.final.head_ros_class],
    ["Dirección", (m) => (m.final.head_direction_deg === null ? "isótropo" : `${num(m.final.head_direction_deg)}°`)],
    ["Elongación", (m) => num(m.final.aspect_ratio, 2)],
  ];

  const ratio =
    a.metrics && b.metrics && b.metrics.final.burned_ha > 0
      ? a.metrics.final.burned_ha / b.metrics.final.burned_ha
      : null;

  return (
    <div className="rounded-md border">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="p-1.5 text-left font-medium">Métrica</th>
            <th className="p-1.5 text-right font-medium">A</th>
            <th className="p-1.5 text-right font-medium">B</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, render]) => (
            <tr key={label} className="border-b last:border-0">
              <td className="p-1.5 text-muted-foreground">{label}</td>
              <td className="p-1.5 text-right tabular-nums">{a.metrics ? render(a.metrics) : "—"}</td>
              <td className="p-1.5 text-right tabular-nums">{b.metrics ? render(b.metrics) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {ratio !== null && (
        <p className="border-t p-1.5 text-[11px]">
          A quema <strong>{num(ratio, 2)}×</strong> lo de B.
        </p>
      )}

      {[a, b].some((s) => s.metrics?.reached_domain_edge) && (
        <p className="border-t bg-destructive/10 p-1.5 text-[11px] text-destructive">
          Un frente tocó el borde del dominio: quedó recortado y la comparación no es
          válida. Ampliá <code>domain_size_m</code> o acortá <code>tstop_s</code>.
        </p>
      )}
    </div>
  );
}
