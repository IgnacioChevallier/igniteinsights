"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle, RefreshCw, TriangleAlert } from "lucide-react";
import { EnsembleAgreementLegend } from "@/components/ensemble-agreement-legend";
import { FireMap, type RasterOverlayData } from "@/components/fire-map";
import { FireAnimationControls } from "@/components/fire-animation-controls";
import { FireGrowthStatsPanel, type FireSizeStatsRow } from "@/components/fire-growth-stats-panel";
import { RasterLegend } from "@/components/raster-legend";
import { SettingsButton } from "@/components/settings-button";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useFireClock } from "@/hooks/use-fire-clock";
import { realTimestamp, snapToLevel, summarizeIsochrones } from "@/lib/isochrone-clock";
import { geoJsonAreaHa, isochroneAreaHa } from "@/lib/geojson-area";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";
import {
  describeSettings,
  loadSettings,
  runRealSimulation,
  type IngestionSettings,
  type RunPhase,
} from "@/lib/real-run";
import {
  WIND_SPEED_GRADIENT,
  type GriddedWindField,
  type WindBand,
} from "@/lib/wind-particles";
import type { Run } from "@/lib/dashboard-types";
import {
  checkEnsembleAgreement,
  ENSEMBLE_AGREEMENT_LAYER,
  type EnsembleAgreementContract,
} from "@/lib/ensemble-agreement";

/** GET /api/simulations/{id}/wind — the run's own ws/wd rasters, per hourly band. */
export type WindFieldResponse = {
  schema_version: 2;
  bounds: [number, number, number, number];
  ring: [number, number][];
  width: number;
  height: number;
  unit: "mph";
  basis: "elmfire_20ft";
  height_m: number;
  source_model: string;
  forecast_start: string | null;
  forecast_cycle: string | null;
  step_hours: number;
  bands: WindBand[];
};

function formatOptionLabel(run: Run) {
  const shortId = run.id.length > 8 ? `${run.id.slice(0, 8)}...` : run.id;
  const started = run.started_at ? formatArgentinaDateTime(run.started_at) : "hora desconocida";
  const horizon = run.horizon_hours ? ` (${run.horizon_hours}h)` : "";
  return `${shortId} - ${started} ${ARGENTINA_TIME_ZONE_LABEL}${horizon} [${statusLabel(run.status)}]`;
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
  return `Periodo de predicción: ${formatArgentinaDateTime(start)} → ${formatArgentinaDateTime(end)} ${ARGENTINA_TIME_ZONE_LABEL}`;
}

class DataRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DataRequestError";
  }
}

function responseErrorMessage(envelope: Record<string, unknown>, statusCode: number): string {
  if (typeof envelope.detail === "string") return envelope.detail;
  if (typeof envelope.error === "string") return envelope.error;
  return `El servidor respondió HTTP ${statusCode}.`;
}

async function fetchJsonOrThrow<T>(url: string, signal?: AbortSignal): Promise<T | null> {
  const res = await fetch(url, { cache: "no-store", signal });
  let envelope: Record<string, unknown>;
  try {
    envelope = (await res.json()) as Record<string, unknown>;
  } catch {
    throw new DataRequestError("El servidor devolvió una respuesta que no se pudo leer.");
  }
  if (!res.ok) throw new DataRequestError(responseErrorMessage(envelope, res.status));
  return (envelope.data as T | null | undefined) ?? null;
}

async function fetchJson<T>(url: string, signal?: AbortSignal): Promise<T | null> {
  try {
    return await fetchJsonOrThrow<T>(url, signal);
  } catch {
    return null;
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Error inesperado al cargar el resultado.";
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

type MapResultState = "idle" | "loading" | "ready" | "error";

const DEFAULT_VISIBLE_HORIZON_HOURS = 3;
const MAX_VISIBLE_HORIZON_HOURS = 25;

function MapResultNotice({
  state,
  error,
  onRetry,
}: {
  state: MapResultState;
  error: string | null;
  onRetry: () => void;
}) {
  if (state === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none absolute left-1/2 top-4 z-20 flex w-[min(23rem,calc(100%-2rem))] -translate-x-1/2 items-start gap-3 rounded-md border border-amber-500/40 bg-card/95 px-3 py-2.5 shadow-lg backdrop-blur"
      >
        <LoaderCircle className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-amber-600" />
        <div>
          <p className="text-xs font-medium text-foreground">Procesando resultado cartográfico</p>
          <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
            Convirtiendo la salida de ELMFIRE en isócronas. En dominios grandes puede tardar cerca de
            un minuto.
          </p>
        </div>
      </div>
    );
  }

  if (state !== "error") return null;
  return (
    <div
      role="alert"
      className="absolute left-1/2 top-4 z-20 flex w-[min(25rem,calc(100%-2rem))] -translate-x-1/2 items-start gap-3 rounded-md border border-destructive/50 bg-card/95 px-3 py-2.5 shadow-lg backdrop-blur"
    >
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-foreground">No se pudo cargar el resultado</p>
        <p className="mt-0.5 break-words text-[11px] leading-snug text-muted-foreground">
          {error}
        </p>
        <Button className="mt-2 gap-1.5" size="sm" variant="outline" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </div>
  );
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
const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

function RealRunLauncher({ onFinished }: { onFinished: (simulationId: string | null) => void }) {
  const [phase, setPhase] = useState<RunPhase>(null);
  const [error, setError] = useState<string | null>(null);
  // A real ingestion measured 452 s. Without a running count it is indistinguishable from
  // a hang, which is exactly how it was reported.
  const [elapsed, setElapsed] = useState(0);
  // localStorage is unreadable while rendering on the server, so the summary waits for
  // mount rather than rendering a guess the first paint would then contradict.
  const [settings, setSettings] = useState<IngestionSettings | null>(null);

  const summary = settings && describeSettings(settings);

  useEffect(() => {
    if (!phase) return;
    setElapsed(0);
    const started = Date.now();
    const id = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, [phase]);

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
            ? `Ingestando datos… ${mmss(elapsed)}`
            : phase === "simulating"
              ? `Simulando… ${mmss(elapsed)}`
              : "Ejecutar simulación real"}
        </Button>
        {/* Right next to the button it configures, and the same page the header opens —
            the sources have one home, not one per entry point. */}
        <SettingsButton variant="outline" title="Configurar fuentes de ingesta" />
      </div>

      {/* The window is the one thing that changes between runs, so it is also the way in
          to change it: as plain text it read as a fixed property of the button. */}
      {summary && (
        <a
          href="/settings"
          className="text-[11px] leading-snug text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground"
        >
          {summary}
        </a>
      )}

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

  // Follow the newest run whenever one arrives. The launcher in this panel selects the id
  // it just produced, but the "Datos" header runs the same simulation from a sibling
  // component that cannot reach this state — it only calls `router.refresh()`, so the new
  // run landed in the dropdown while the map went on showing the previous selection. This
  // keys on `defaultRunId`, which only moves when a genuinely newer run appears, so a
  // manual pick from the dropdown survives an ordinary refresh.
  useEffect(() => {
    if (defaultRunId) setSelectedRunId(defaultRunId);
  }, [defaultRunId]);
  const [activeFires, setActiveFires] = useState<GeoJSON.FeatureCollection | null>(null);
  const [isochrones, setIsochrones] = useState<GeoJSON.FeatureCollection | null>(null);
  const [ignitionPerimeter, setIgnitionPerimeter] = useState<GeoJSON.FeatureCollection | null>(
    null,
  );
  const [statsRow, setStatsRow] = useState<FireSizeStatsRow | null>(null);
  const [wind, setWind] = useState<WindFieldResponse | null>(null);
  const [mapResultState, setMapResultState] = useState<MapResultState>(
    selectedRunId ? "loading" : "idle",
  );
  const [mapResultError, setMapResultError] = useState<string | null>(null);
  const [auxiliaryLoading, setAuxiliaryLoading] = useState(false);
  const [auxiliaryErrors, setAuxiliaryErrors] = useState<string[]>([]);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [visibleHorizonHours, setVisibleHorizonHours] = useState(
    DEFAULT_VISIBLE_HORIZON_HOURS,
  );

  const [showTimeOfArrival, setShowTimeOfArrival] = useState(false);
  const [showFirelineIntensity, setShowFirelineIntensity] = useState(false);
  const [showEnsembleAgreement, setShowEnsembleAgreement] = useState<boolean>(
    ENSEMBLE_AGREEMENT_LAYER.defaultVisible,
  );
  const [ensembleAgreement, setEnsembleAgreement] = useState<EnsembleAgreementContract | null>(
    null,
  );
  const [ensembleAgreementIssue, setEnsembleAgreementIssue] = useState<string | null>(null);
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
  const availableHorizonHours = summary.horizonHours || selectedRun?.horizon_hours || 0;
  const maxVisibleHorizonHours = Math.min(availableHorizonHours, MAX_VISIBLE_HORIZON_HOURS);
  const horizonHours = Math.min(visibleHorizonHours, maxVisibleHorizonHours);
  const animatable = summary.timedCount > 0 && horizonHours > 0;
  // Gated on `animatable`, not just on the horizon: a run whose isochrones carry no times
  // hides the controls and ignores the clock, but the clock still autoplayed and wrote
  // state every animation frame. That re-rendered this panel ~24x a second forever, for
  // nothing anyone could see.
  const clock = useFireClock({ horizonHours: animatable ? horizonHours : 0 });
  // The scrubber and the timestamp follow `clock.t` at 60 fps because they are text and
  // a slider. The map must not: its filters select `arrival_hours <= t` over a source
  // with ~90k vertices, so every frame re-evaluated and re-tessellated the whole thing to
  // produce a picture identical to the previous one — the levels are discrete, the clock
  // is not. Snapping makes this object change once per isochrone (12 times a loop here)
  // instead of 60 times a second, which is the difference between the animation dropping
  // frames and it not.
  const snappedT = snapToLevel(clock.t, summary.levels);
  const clockView = useMemo(
    () => ({ t: snappedT, stepHours: summary.stepHours, horizonHours }),
    [snappedT, summary.stepHours, horizonHours],
  );
  const visibleIsochrones = useMemo<GeoJSON.FeatureCollection | null>(() => {
    if (!isochrones) return null;
    return {
      ...isochrones,
      features: isochrones.features.filter((feature) => {
        const arrival = Number(feature.properties?.arrival_hours);
        return Number.isFinite(arrival) && arrival <= horizonHours;
      }),
    };
  }, [isochrones, horizonHours]);
  const observedAreaHa = useMemo(
    () => geoJsonAreaHa(ignitionPerimeter),
    [ignitionPerimeter],
  );
  const predictedAreaHa = useMemo(
    () => isochroneAreaHa(isochrones, horizonHours),
    [isochrones, horizonHours],
  );

  useEffect(() => {
    setVisibleHorizonHours(DEFAULT_VISIBLE_HORIZON_HOURS);
  }, [selectedRunId]);

  useEffect(() => {
    fetchJson<GeoJSON.FeatureCollection>("/api/fires/active?hours=24").then(setActiveFires);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;

    setTimeOfArrivalOverlay(null);
    setFirelineIntensityOverlay(null);
    setEnsembleAgreement(null);
    setEnsembleAgreementIssue(null);
    setIsochrones(null);
    setIgnitionPerimeter(null);
    setStatsRow(null);
    setWind(null);
    setMapResultError(null);
    setAuxiliaryErrors([]);
    setAuxiliaryLoading(false);

    if (!selectedRunId) {
      setMapResultState("idle");
      return;
    }

    setMapResultState("loading");

    async function loadRunResult() {
      try {
        // This is the map's primary result and the expensive request the operator is
        // waiting for. Give it the API's CPU and disk bandwidth before starting any of
        // the supplementary layers — especially wind, which reads two large rasters.
        const nextIsochrones = await fetchJsonOrThrow<GeoJSON.FeatureCollection>(
          `/api/simulations/${selectedRunId}/isochrones`,
          controller.signal,
        );
        if (!current) return;
        setIsochrones(nextIsochrones);
        setMapResultState("ready");

        setAuxiliaryLoading(true);
        const [ignitionResult, statsResult] = await Promise.allSettled([
          fetchJsonOrThrow<GeoJSON.FeatureCollection>(
            `/api/simulations/${selectedRunId}/ignition`,
            controller.signal,
          ),
          fetchJsonOrThrow<{ rows: FireSizeStatsRow[] }>(
            `/api/simulations/${selectedRunId}/stats`,
            controller.signal,
          ),
        ]);
        if (!current) return;

        const failures: string[] = [];
        if (ignitionResult.status === "fulfilled") {
          setIgnitionPerimeter(ignitionResult.value);
        } else if (!isAbortError(ignitionResult.reason)) {
          failures.push(`perímetro inicial: ${errorMessage(ignitionResult.reason)}`);
        }
        if (statsResult.status === "fulfilled") {
          setStatsRow(statsResult.value?.rows?.[0] ?? null);
        } else if (!isAbortError(statsResult.reason)) {
          failures.push(`resumen: ${errorMessage(statsResult.reason)}`);
        }

        try {
          const nextWind = await fetchJsonOrThrow<WindFieldResponse>(
            `/api/simulations/${selectedRunId}/wind`,
            controller.signal,
          );
          if (current) setWind(nextWind);
        } catch (error) {
          if (!isAbortError(error)) failures.push(`viento: ${errorMessage(error)}`);
        }
        if (current) setAuxiliaryErrors(failures);
      } catch (error) {
        if (!current || isAbortError(error)) return;
        setMapResultError(errorMessage(error));
        setMapResultState("error");
      } finally {
        if (current) setAuxiliaryLoading(false);
      }
    }

    void loadRunResult();
    return () => {
      current = false;
      controller.abort();
    };
  }, [selectedRunId, loadAttempt]);

  // The renderer owns fractional-time interpolation. This object changes only when a new
  // run is loaded, so 60 fps clock updates never clear or reseed its particle trails.
  const windHour = Math.min(
    Math.floor(clock.t / (wind?.step_hours || 1)),
    Math.max((wind?.bands.length ?? 1) - 1, 0),
  );
  const windBand = wind?.bands[windHour] ?? null;
  const windField = useMemo<GriddedWindField | null>(() => {
    if (!wind?.bands.length) return null;
    return {
      kind: "gridded",
      bounds: wind.bounds,
      ring: wind.ring,
      width: wind.width,
      height: wind.height,
      stepHours: wind.step_hours,
      bands: wind.bands,
    };
  }, [wind]);

  const windValidTime = useMemo(() => {
    if (!wind?.forecast_start) return null;
    const start = new Date(wind.forecast_start);
    if (!Number.isFinite(start.getTime())) return null;
    return formatArgentinaDateTime(new Date(start.getTime() + clock.t * 3600_000));
  }, [wind?.forecast_start, clock.t]);

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

  // Lazy like the two rasters: nothing is requested until the box is ticked. A missing or
  // partial artifact becomes a sidebar note; the map keeps whatever it was showing.
  useEffect(() => {
    if (!showEnsembleAgreement || !selectedRunId || ensembleAgreement || ensembleAgreementIssue) {
      return;
    }
    const controller = new AbortController();
    fetchJsonOrThrow<unknown>(
      `/api/simulations/${selectedRunId}/ensemble-agreement`,
      controller.signal,
    )
      .then((data) => {
        const checked = checkEnsembleAgreement(data);
        if (typeof checked === "string") setEnsembleAgreementIssue(checked);
        else setEnsembleAgreement(checked);
      })
      .catch((error) => {
        if (!isAbortError(error)) {
          setEnsembleAgreementIssue("No hay acuerdo del ensamble disponible para esta ejecución.");
        }
      });
    return () => controller.abort();
  }, [showEnsembleAgreement, selectedRunId, ensembleAgreement, ensembleAgreementIssue]);

  // Thematic backgrounds share the map: agreement excludes both rasters and vice versa.
  // Arrival and intensity together keep working as they did before this layer existed.
  const toggleEnsembleAgreement = (checked: boolean) => {
    setShowEnsembleAgreement(checked);
    if (checked) {
      setShowTimeOfArrival(false);
      setShowFirelineIntensity(false);
    }
  };

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
          ensembleAgreement={showEnsembleAgreement ? ensembleAgreement : null}
          fitTo={visibleIsochrones}
          windField={windField}
          windTimeHours={clock.t}
          clock={animatable ? clockView : null}
          overlay={
            animatable ? (
              <FireAnimationControls
                clock={clock}
                untimedCount={summary.untimedCount}
                horizonControl={{
                  valueHours: horizonHours,
                  maxHours: maxVisibleHorizonHours,
                  onChange: setVisibleHorizonHours,
                }}
              />
            ) : null
          }
        />
        <MapResultNotice
          state={mapResultState}
          error={mapResultError}
          onRetry={() => setLoadAttempt((attempt) => attempt + 1)}
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
            // Same border, height, radius and shadow as the buttons around it: at a
            // different height and a bare border it read as a form field dropped into a
            // toolbar.
            className="mt-1 h-8 w-full rounded-md border border-input bg-background px-2 text-xs shadow-sm transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
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
          {auxiliaryLoading && mapResultState === "ready" && (
            <p role="status" className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <LoaderCircle className="h-3 w-3 animate-spin text-amber-600" />
              Completando perímetro, métricas y viento…
            </p>
          )}
          {auxiliaryErrors.length > 0 && (
            <div
              role="alert"
              className="mt-2 rounded-md border border-amber-500/40 bg-amber-500/10 p-2 text-[11px] leading-snug text-muted-foreground"
            >
              <p className="flex items-center gap-1 font-medium text-foreground">
                <TriangleAlert className="h-3.5 w-3.5 text-amber-600" />
                Algunas capas no se cargaron
              </p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">
                {auxiliaryErrors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
              <Button
                className="mt-2 gap-1.5"
                size="sm"
                variant="outline"
                onClick={() => setLoadAttempt((attempt) => attempt + 1)}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Reintentar capas
              </Button>
            </div>
          )}
        </div>

        {/* Motion, colour and words carry different information: flow direction, local
            speed and a screenshot-safe summary respectively. */}
        {windBand && (
          <div className="rounded-md border border-slate-300/70 bg-slate-50/70 p-2.5 dark:border-slate-700 dark:bg-slate-900/40">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-medium text-foreground">{windBand.label}</p>
              <span className="shrink-0 rounded-full border border-slate-300 bg-white px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-slate-600 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-300">
                20 ft
              </span>
            </div>
            <div
              className="mt-2 h-1.5 rounded-full shadow-inner"
              style={{ background: WIND_SPEED_GRADIENT }}
              aria-label="Escala de velocidad del viento de 0 a 40 mph"
            />
            <div className="mt-0.5 flex justify-between text-[9px] tabular-nums text-muted-foreground">
              <span>0</span><span>20</span><span>40+ mph</span>
            </div>
            <p className="mt-1 text-[9px] leading-snug text-muted-foreground">
              El color de cada línea indica la velocidad del viento.
            </p>
            <p className="mt-2 text-[10px] leading-snug text-muted-foreground">
              {(wind?.source_model ?? "GFS 0,25°").replace("0.25", "0,25")} · entrada de
              ELMFIRE a 6,1 m
            </p>
            <p className="mt-0.5 text-[10px] leading-snug text-muted-foreground">
              {windValidTime
                ? `Hora válida: ${windValidTime} ${ARGENTINA_TIME_ZONE_LABEL}`
                : "Hora válida no disponible"}
              {wind?.forecast_cycle ? ` · ciclo ${wind.forecast_cycle}` : ""}
            </p>
            <p className="mt-1 text-[9px] leading-snug text-muted-foreground/80">
              La interpolación suaviza la lectura; no agrega detalle local al GFS de 0,25°.
            </p>
          </div>
        )}

        <RunWarnings warnings={selectedRun?.warnings} />

        <Separator />

        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={showTimeOfArrival}
              onChange={(e) => {
                setShowTimeOfArrival(e.target.checked);
                if (e.target.checked) setShowEnsembleAgreement(false);
              }}
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
              onChange={(e) => {
                setShowFirelineIntensity(e.target.checked);
                if (e.target.checked) setShowEnsembleAgreement(false);
              }}
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

          <div className="mt-1 flex items-center justify-between gap-3">
            <label
              htmlFor="admin-ensemble-agreement"
              className="text-xs font-medium uppercase tracking-wide text-muted-foreground"
            >
              {ENSEMBLE_AGREEMENT_LAYER.name}
            </label>
            <Switch
              id="admin-ensemble-agreement"
              checked={showEnsembleAgreement}
              onCheckedChange={toggleEnsembleAgreement}
            />
          </div>
          {showEnsembleAgreement && ensembleAgreement && (
            <EnsembleAgreementLegend contract={ensembleAgreement} />
          )}
          {showEnsembleAgreement && ensembleAgreementIssue && (
            <p role="status" className="text-[11px] leading-snug text-muted-foreground">
              {ensembleAgreementIssue}
            </p>
          )}
        </div>

        <Separator />

        <FireGrowthStatsPanel
          timestamp={realTimestamp(selectedRun?.ignition_datetime, Math.round(clock.t * 10) / 10)}
          row={statsRow}
          observedAreaHa={observedAreaHa}
          predictedAreaHa={predictedAreaHa}
          horizonHours={horizonHours}
        />
      </aside>
    </div>
  );
}
