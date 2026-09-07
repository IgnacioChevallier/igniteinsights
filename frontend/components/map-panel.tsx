"use client";

import { useEffect, useMemo, useState } from "react";
import { FireMap, type RasterOverlayData } from "@/components/fire-map";
import { FireGrowthStatsPanel, type FireSizeStatsRow } from "@/components/fire-growth-stats-panel";
import { RasterLegend } from "@/components/raster-legend";
import { Separator } from "@/components/ui/separator";
import type { Run } from "@/lib/dashboard-types";

function formatOptionLabel(run: Run) {
  const shortId = run.id.length > 8 ? `${run.id.slice(0, 8)}...` : run.id;
  const started = run.started_at
    ? new Intl.DateTimeFormat("es", {
        timeZone: "UTC",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(run.started_at))
    : "hora desconocida";
  const horizon = run.horizon_hours ? ` (${run.horizon_hours}h)` : "";
  return `${shortId} - ${started}${horizon} [${statusLabel(run.status)}]`;
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: "Completado",
    error: "Error",
    failed: "Fallido",
    incomplete: "Incompleto",
    none: "Sin datos",
    partial_failure: "Falla parcial",
    pending: "Pendiente",
    ready: "Listo",
    running: "En ejecución",
    skipped: "Omitido",
    success: "Éxito",
  };
  return labels[status.toLowerCase()] ?? status;
}

function formatPredictedPeriod(run: Run | undefined) {
  if (!run || !run.ignition_datetime) {
    return "Periodo de predicción desconocido (ejecución heredada: no se registró la hora de ignición).";
  }
  const start = new Date(run.ignition_datetime);
  const end = new Date(start.getTime() + (run.horizon_hours ?? 0) * 3600_000);
  const fmt = new Intl.DateTimeFormat("es", {
    timeZone: "UTC",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  return `Periodo de predicción: ${fmt.format(start)} → ${fmt.format(end)}`;
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    const envelope = await res.json();
    return envelope.data ?? null;
  } catch {
    return null;
  }
}

// Caveats that change how the result should be read but leave it looking normal on the
// map — today: weather rasters with a single band, i.e. no diurnal cycle for the run.
function RunWarnings({ warnings }: { warnings?: string[] | null }) {
  if (!warnings?.length) return null;
  return (
    <div
      role="status"
      className="rounded-md border border-amber-500/50 bg-amber-500/10 p-2 text-xs"
    >
      <p className="mb-1 font-medium text-amber-700 dark:text-amber-400">
        ⚠ Advertencias de esta corrida
      </p>
      <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
        {warnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
    </div>
  );
}

export function MapPanel({ runs }: { runs: Run[] }) {
  const simulationRuns = useMemo(() => runs.filter((r) => r.kind === "simulation"), [runs]);

  const defaultRunId = useMemo(() => {
    return simulationRuns.find((r) => r.status === "success")?.id ?? simulationRuns[0]?.id ?? null;
  }, [simulationRuns]);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(defaultRunId);
  const [activeFires, setActiveFires] = useState<GeoJSON.FeatureCollection | null>(null);
  const [isochrones, setIsochrones] = useState<GeoJSON.FeatureCollection | null>(null);
  const [ignitionPerimeter, setIgnitionPerimeter] = useState<GeoJSON.FeatureCollection | null>(
    null,
  );
  const [statsRow, setStatsRow] = useState<FireSizeStatsRow | null>(null);

  const [showTimeOfArrival, setShowTimeOfArrival] = useState(false);
  const [showFirelineIntensity, setShowFirelineIntensity] = useState(false);
  const [timeOfArrivalOverlay, setTimeOfArrivalOverlay] = useState<RasterOverlayData | null>(null);
  const [firelineIntensityOverlay, setFirelineIntensityOverlay] = useState<RasterOverlayData | null>(
    null,
  );

  const selectedRun = simulationRuns.find((r) => r.id === selectedRunId);

  useEffect(() => {
    fetchJson<GeoJSON.FeatureCollection>("/api/fires/active?hours=24").then(setActiveFires);
  }, []);

  useEffect(() => {
    setTimeOfArrivalOverlay(null);
    setFirelineIntensityOverlay(null);
    if (!selectedRunId) {
      setIsochrones(null);
      setIgnitionPerimeter(null);
      setStatsRow(null);
      return;
    }
    fetchJson<GeoJSON.FeatureCollection>(`/api/simulations/${selectedRunId}/isochrones`).then(
      setIsochrones,
    );
    fetchJson<GeoJSON.FeatureCollection>(`/api/simulations/${selectedRunId}/ignition`).then(
      setIgnitionPerimeter,
    );
    fetchJson<{ rows: FireSizeStatsRow[] }>(`/api/simulations/${selectedRunId}/stats`).then(
      (data) => setStatsRow(data?.rows?.[0] ?? null),
    );
  }, [selectedRunId]);

  useEffect(() => {
    if (!showTimeOfArrival || !selectedRunId || timeOfArrivalOverlay) return;
    fetchJson<RasterOverlayData>(`/api/simulations/${selectedRunId}/rasters/time_of_arrival`).then(
      setTimeOfArrivalOverlay,
    );
  }, [showTimeOfArrival, selectedRunId, timeOfArrivalOverlay]);

  useEffect(() => {
    if (!showFirelineIntensity || !selectedRunId || firelineIntensityOverlay) return;
    fetchJson<RasterOverlayData>(
      `/api/simulations/${selectedRunId}/rasters/fireline_intensity`,
    ).then(setFirelineIntensityOverlay);
  }, [showFirelineIntensity, selectedRunId, firelineIntensityOverlay]);

  if (!simulationRuns.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Aún no hay ejecuciones de simulación. Ejecuta una simulación para verla en el mapa.
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="relative min-h-0 flex-1">
        <FireMap
          activeFires={activeFires}
          isochrones={isochrones}
          ignitionPerimeter={ignitionPerimeter}
          timeOfArrivalOverlay={showTimeOfArrival ? timeOfArrivalOverlay : null}
          firelineIntensityOverlay={showFirelineIntensity ? firelineIntensityOverlay : null}
        />
      </div>

      <aside className="flex w-56 shrink-0 flex-col gap-4 overflow-auto border-l bg-background p-3">
        <div>
          <label htmlFor="simulation-select" className="text-xs text-muted-foreground">
            Ejecución de simulación
          </label>
          <select
            id="simulation-select"
            className="mt-1 w-full rounded-md border bg-background px-2 py-1 text-xs"
            value={selectedRunId ?? ""}
            onChange={(e) => setSelectedRunId(e.target.value)}
          >
            {simulationRuns.map((run) => (
              <option key={run.id} value={run.id}>
                {formatOptionLabel(run)}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs text-muted-foreground">{formatPredictedPeriod(selectedRun)}</p>
        </div>

        <RunWarnings warnings={selectedRun?.warnings} />

        <Separator />

        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={showTimeOfArrival}
              onChange={(e) => setShowTimeOfArrival(e.target.checked)}
            />
            Tiempo de llegada
          </label>
          {showTimeOfArrival && timeOfArrivalOverlay && (
            <RasterLegend
              label="Tiempo de llegada"
              valueRange={timeOfArrivalOverlay.value_range}
              unit={timeOfArrivalOverlay.unit}
            />
          )}

          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={showFirelineIntensity}
              onChange={(e) => setShowFirelineIntensity(e.target.checked)}
            />
            Intensidad del frente de fuego
          </label>
          {showFirelineIntensity && firelineIntensityOverlay && (
            <RasterLegend
              label="Intensidad del frente de fuego"
              valueRange={firelineIntensityOverlay.value_range}
              unit={firelineIntensityOverlay.unit}
            />
          )}
        </div>

        <Separator />

        <FireGrowthStatsPanel row={statsRow} />
      </aside>
    </div>
  );
}
