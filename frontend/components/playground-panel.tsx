"use client";

import { useEffect, useState } from "react";
import { FireMap } from "@/components/fire-map";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

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

type Slot = {
  preset: Preset | null;
  isochrones: GeoJSON.FeatureCollection | null;
  metrics: Metrics | null;
  status: "idle" | "running" | "error";
  error?: string;
};

const EMPTY_SLOT: Slot = { preset: null, isochrones: null, metrics: null, status: "idle" };

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
  };
}

export function PlaygroundPanel() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [slots, setSlots] = useState<[Slot, Slot]>([EMPTY_SLOT, EMPTY_SLOT]);

  useEffect(() => {
    fetch("/api/playground/presets", { cache: "no-store" })
      .then(async (res) => {
        const env = await res.json();
        if (!res.ok || !env.data) throw new Error(env.detail ?? "Sin datos");
        setPresets(env.data.presets as Preset[]);
      })
      .catch((e: Error) => setLoadError(e.message));
  }, []);

  const run = async (preset: Preset, slotIndex: 0 | 1) => {
    setSlots((prev) => {
      const next: [Slot, Slot] = [prev[0], prev[1]];
      next[slotIndex] = { preset, isochrones: null, metrics: null, status: "running" };
      return next;
    });
    try {
      const { isochrones, metrics } = await runScenario(preset.scenario);
      setSlots((prev) => {
        const next: [Slot, Slot] = [prev[0], prev[1]];
        next[slotIndex] = { preset, isochrones, metrics, status: "idle" };
        return next;
      });
    } catch (e) {
      setSlots((prev) => {
        const next: [Slot, Slot] = [prev[0], prev[1]];
        next[slotIndex] = {
          preset, isochrones: null, metrics: null,
          status: "error", error: (e as Error).message,
        };
        return next;
      });
    }
  };

  const groups = Array.from(new Set(presets.map((p) => p.group)));

  return (
    <div className="flex h-full">
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="border-b bg-amber-50 px-3 py-1.5 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-100">
          Dominios <strong>sintéticos</strong>: terreno, combustible y viento uniformes. Se
          dibujan sobre el AOI sólo para dar escala — no son una predicción para ese lugar.
        </div>
        <div className="grid min-h-0 flex-1 grid-cols-2 divide-x">
          {slots.map((slot, i) => (
            <div key={i} className="relative min-h-0">
              <FireMap isochrones={slot.isochrones} fitTo={slot.isochrones} />
              <div className="pointer-events-none absolute left-2 top-2 z-10 max-w-[80%] rounded-md bg-background/90 px-2 py-1 text-xs shadow">
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
