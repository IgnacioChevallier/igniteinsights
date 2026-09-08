"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { FireMap, type RasterOverlayData } from "@/components/fire-map";
import { FireAnimationControls } from "@/components/fire-animation-controls";
import { FireGrowthStatsPanel, type FireSizeStatsRow } from "@/components/fire-growth-stats-panel";
import { RasterLegend } from "@/components/raster-legend";
import { SettingsButton } from "@/components/settings-button";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useFireClock } from "@/hooks/use-fire-clock";
import { summarizeIsochrones } from "@/lib/isochrone-clock";
import {
  describeSettings,
  loadSettings,
  runRealSimulation,
  type IngestionSettings,
  type RunPhase,
} from "@/lib/real-run";
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

/**
 * Launch a real run from where its result will appear.
 *
 * The same ingest → prepare → simulate the "Datos" header runs, and deliberately the same
 * implementation: the sources it pulls are whatever `/settings` holds, so this button
 * cannot quietly download the ~500 MB canopy layer that page says to leave alone. What it
 * will pull is spelled out above the button rather than left to be discovered.
 */
function RealRunLauncher({ onFinished }: { onFinished: (simulationId: string | null) => void }) {
  const [phase, setPhase] = useState<RunPhase>(null);
  const [error, setError] = useState<string | null>(null);
  // localStorage is unreadable while rendering on the server, so the summary waits for
  // mount rather than rendering a guess the first paint would then contradict.
  const [settings, setSettings] = useState<IngestionSettings | null>(null);

  useEffect(() => {
    const read = () => setSettings(loadSettings());
    read();
    // The sources are edited on another page, and coming back from it can restore this
    // one from the bfcache, where mount effects do not run again — the summary would then
    // keep advertising sources the settings page has already changed.
    window.addEventListener("pageshow", read);
    window.addEventListener("focus", read);
    return () => {
      window.removeEventListener("pageshow", read);
      window.removeEventListener("focus", read);
    };
  }, []);

  const run = async () => {
    if (!settings) return;
    setError(null);
    try {
      onFinished(await runRealSimulation(settings, setPhase));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setPhase(null);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5">
        <Button
          size="sm"
          className="flex-1"
          onClick={run}
          disabled={phase !== null || !settings}
        >
          {phase === "ingesting"
            ? "Ingestando datos…"
            : phase === "simulating"
              ? "Simulando…"
              : "Ejecutar simulación real"}
        </Button>
        {/* Right next to the button it configures, and the same page the header opens —
            the sources have one home, not one per entry point. */}
        <SettingsButton variant="outline" />
      </div>

      {settings && (
        <ul className="space-y-0.5 text-[11px] leading-snug text-muted-foreground">
          {describeSettings(settings).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      <p className="text-[11px] leading-snug text-muted-foreground">
        Las fuentes se configuran con el engranaje. Tarda minutos: descarga, deriva los
        rásteres y corre ELMFIRE.
      </p>

      {error && <p className="text-[11px] leading-snug text-destructive">{error}</p>}
    </div>
  );
}

export function MapPanel({ runs }: { runs: Run[] }) {
  const router = useRouter();
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

  // Show what was just produced. `router.refresh()` re-fetches the server data that feeds
  // the run list; selecting the id straight away means the map does not wait for it.
  const handleRunFinished = (simulationId: string | null) => {
    if (simulationId) setSelectedRunId(simulationId);
    router.refresh();
  };

  // The horizon and the isochrone step both come out of the GeoJSON itself; the run's
  // declared horizon_hours is only a fallback for a collection with a single level.
  const summary = useMemo(() => summarizeIsochrones(isochrones), [isochrones]);
  const horizonHours = summary.horizonHours || selectedRun?.horizon_hours || 0;
  const animatable = summary.timedCount > 0 && horizonHours > 0;
  // Gated on `animatable`, not just on the horizon: a run whose isochrones carry no times
  // hides the controls and ignores the clock, but the clock still autoplayed and wrote
  // state every animation frame. That re-rendered this panel ~24x a second forever, for
  // nothing anyone could see.
  const clock = useFireClock({ horizonHours: animatable ? horizonHours : 0 });
  const clockView = useMemo(
    () => ({ t: clock.t, stepHours: summary.stepHours, horizonHours }),
    [clock.t, summary.stepHours, horizonHours],
  );

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

  // The cold start told the operator to run a simulation without offering any way to do
  // it; the only button was on another section.
  if (!simulationRuns.length) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="w-80 max-w-full">
          <p className="mb-3 text-sm text-muted-foreground">
            Aún no hay ejecuciones de simulación.
          </p>
          <RealRunLauncher onFinished={handleRunFinished} />
        </div>
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
          fitTo={isochrones}
          clock={animatable ? clockView : null}
          overlay={
            animatable ? (
              <FireAnimationControls
                clock={clock}
                ignitionDatetime={selectedRun?.ignition_datetime ?? null}
                untimedCount={summary.untimedCount}
              />
            ) : null
          }
        />
      </div>

      <aside className="flex w-72 shrink-0 flex-col gap-4 overflow-auto border-l bg-background p-3">
        <RealRunLauncher onFinished={handleRunFinished} />

        <Separator />

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
