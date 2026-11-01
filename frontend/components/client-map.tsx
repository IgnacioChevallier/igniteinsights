"use client";

import { useEffect, useMemo, useState } from "react";
import { Flame, LoaderCircle, Satellite } from "lucide-react";
import { EnsembleAgreementLegend } from "@/components/ensemble-agreement-legend";
import { FireAnimationControls } from "@/components/fire-animation-controls";
import { FireGrowthStatsPanel, type FireSizeStatsRow } from "@/components/fire-growth-stats-panel";
import { FireMap } from "@/components/fire-map";
import type { WindFieldResponse } from "@/components/map-panel";
import { Separator } from "@/components/ui/separator";
import { Tooltip } from "@/components/ui/tooltip";
import { useFireClock } from "@/hooks/use-fire-clock";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";
import {
  checkEnsembleAgreement,
  ENSEMBLE_AGREEMENT_LAYER,
  type EnsembleAgreementContract,
} from "@/lib/ensemble-agreement";
import { geoJsonAreaHa, isochroneAreaHa } from "@/lib/geojson-area";
import { realTimestamp, snapToLevel, summarizeIsochrones } from "@/lib/isochrone-clock";
import type { Estado, Incendio } from "@/lib/operativo";
import { cn } from "@/lib/utils";
import { compassPoint, WIND_SPEED_GRADIENT, type GriddedWindField } from "@/lib/wind-particles";

const art = (value: string) => `${formatArgentinaDateTime(value)} ${ARGENTINA_TIME_ZONE_LABEL}`;
const localTime = (value: string) => formatArgentinaDateTime(value);
const MPH_TO_KMH = 1.609344;
// Same stops as the particle colours: 40 mph is where the scale tops out.
const WIND_SCALE_KMH = [0, 16, 32, 48, 64];
const DEFAULT_VISIBLE_HORIZON_HOURS = 3;
const MAX_VISIBLE_HORIZON_HOURS = 24;

async function getData<T>(url: string): Promise<T | null> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) return null;
  return ((await res.json()).data as T | null) ?? null;
}

function bboxCollection([w, s, e, n]: Incendio["bbox"]): GeoJSON.FeatureCollection {
  const pad = 0.02;
  return {
    type: "FeatureCollection",
    features: [{
      type: "Feature",
      properties: {},
      geometry: {
        type: "Polygon",
        coordinates: [[[w - pad, s - pad], [e + pad, s - pad], [e + pad, n + pad], [w - pad, n + pad], [w - pad, s - pad]]],
      },
    }],
  };
}

/**
 * What a client sees (docs/dashboard-producto.md §5): is there a fire, and where will it be
 * in the selected forecast window. Observed detections and the forecast isochrones from the last VIIRS pass,
 * wind and the 3D relief; the ensemble agreement only on request. Nothing here starts a
 * computation — the admin decides what is computed, the client only what to look at.
 */
export function ClientMap({
  estado,
  elegido: elegidoExterno = null,
  onElegir,
}: {
  estado: Estado | null;
  /** When `onElegir` is given the page owns the selection (header dropdown) and the sidebar list is hidden. */
  elegido?: string | null;
  onElegir?: (id: string) => void;
}) {
  const [elegidoInterno, setElegido] = useState<string | null>(null);
  const elegido = onElegir ? elegidoExterno : elegidoInterno;
  const incendios = useMemo(() => estado?.incendios ?? [], [estado]);
  const incendio = incendios.find((i) => i.id === elegido) ?? incendios[0] ?? null;
  const simulacionId = incendio?.pronostico?.simulacion_id ?? null;

  const [isochrones, setIsochrones] = useState<GeoJSON.FeatureCollection | null>(null);
  const [perimetro, setPerimetro] = useState<GeoJSON.FeatureCollection | null>(null);
  const [stats, setStats] = useState<FireSizeStatsRow | null>(null);
  const [wind, setWind] = useState<WindFieldResponse | null>(null);
  const [cargando, setCargando] = useState(false);
  const [visibleHorizonHours, setVisibleHorizonHours] = useState(
    DEFAULT_VISIBLE_HORIZON_HOURS,
  );
  const [verAcuerdo, setVerAcuerdo] = useState(false);
  const [acuerdo, setAcuerdo] = useState<EnsembleAgreementContract | null>(null);
  const [acuerdoAviso, setAcuerdoAviso] = useState<string | null>(null);

  useEffect(() => {
    setIsochrones(null);
    setPerimetro(null);
    setStats(null);
    setWind(null);
    setCargando(false);
    setAcuerdo(null);
    setAcuerdoAviso(null);
    if (!simulacionId) return;
    let vigente = true;
    setCargando(true);
    const base = `/api/simulations/${simulacionId}`;
    void (async () => {
      const iso = await getData<GeoJSON.FeatureCollection>(`${base}/isochrones`);
      if (!vigente) return;
      setIsochrones(iso);
      setCargando(false);
      const [ign, st, vi] = await Promise.all([
        getData<GeoJSON.FeatureCollection>(`${base}/ignition`),
        getData<{ rows: FireSizeStatsRow[] }>(`${base}/stats`),
        getData<WindFieldResponse>(`${base}/wind`),
      ]);
      if (!vigente) return;
      setPerimetro(ign);
      setStats(st?.rows?.[0] ?? null);
      setWind(vi);
    })();
    return () => {
      vigente = false;
    };
  }, [simulacionId]);

  useEffect(() => {
    setVisibleHorizonHours(DEFAULT_VISIBLE_HORIZON_HOURS);
  }, [simulacionId]);

  useEffect(() => {
    if (!verAcuerdo || !simulacionId || acuerdo || acuerdoAviso) return;
    void getData<unknown>(`/api/simulations/${simulacionId}/ensemble-agreement`).then((data) => {
      const checked = data ? checkEnsembleAgreement(data) : "Todavía no hay acuerdo del ensamble para este pronóstico.";
      if (typeof checked === "string") setAcuerdoAviso(checked);
      else setAcuerdo(checked);
    });
  }, [verAcuerdo, simulacionId, acuerdo, acuerdoAviso]);

  const summary = useMemo(() => summarizeIsochrones(isochrones), [isochrones]);
  const availableHorizon = summary.horizonHours || estado?.horizonte_h || 0;
  const maxVisibleHorizon = Math.min(availableHorizon, MAX_VISIBLE_HORIZON_HOURS);
  const horizonte = Math.min(visibleHorizonHours, maxVisibleHorizon);
  const animable = summary.timedCount > 0 && horizonte > 0;
  const clock = useFireClock({ horizonHours: animable ? horizonte : 0 });
  const snappedT = snapToLevel(clock.t, summary.levels);
  const clockView = useMemo(
    () => ({ t: snappedT, stepHours: summary.stepHours, horizonHours: horizonte }),
    [snappedT, summary.stepHours, horizonte],
  );
  const visibleIsochrones = useMemo<GeoJSON.FeatureCollection | null>(() => {
    if (!isochrones) return null;
    return {
      ...isochrones,
      features: isochrones.features.filter((feature) => {
        const arrival = Number(feature.properties?.arrival_hours);
        return Number.isFinite(arrival) && arrival <= horizonte;
      }),
    };
  }, [isochrones, horizonte]);
  const observedAreaHa = useMemo(() => geoJsonAreaHa(perimetro), [perimetro]);
  const predictedAreaHa = useMemo(
    () => isochroneAreaHa(isochrones, horizonte),
    [isochrones, horizonte],
  );

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

  const encuadre = useMemo(
    () => isochrones ?? (incendio ? bboxCollection(incendio.bbox) : null),
    [isochrones, incendio],
  );
  const pronostico = incendio?.pronostico ?? null;
  const shownT = Math.round(clock.t * 10) / 10;
  const stamp = realTimestamp(pronostico?.pasada, shownT);
  const windBand =
    wind?.bands[Math.min(Math.floor(clock.t / (wind.step_hours || 1)), wind.bands.length - 1)] ?? null;

  return (
    <div className="flex h-full min-h-0 flex-col md:flex-row">
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="relative min-h-0 flex-1">
          <FireMap
            activeFires={estado?.detecciones ?? null}
            isochrones={visibleIsochrones}
            ignitionPerimeter={perimetro}
            ensembleAgreement={verAcuerdo ? acuerdo : null}
            fitTo={encuadre}
            windField={windField}
            windTimeHours={clock.t}
            windSurfaceVisible={false}
            clock={animable ? clockView : null}
            overlay={
              animable ? (
                <FireAnimationControls clock={clock} />
              ) : null
            }
          />
          {estado && !incendios.length && (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4">
              <div className="rounded-lg border bg-background/95 px-4 py-3 text-sm shadow-md">
                <p className="font-medium">Sin focos activos detectados.</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Última pasada VIIRS: {estado.ultima_pasada ? art(estado.ultima_pasada) : "sin detecciones en 7 días"} ·
                  Próxima estimada: ~{art(estado.proxima_pasada_estimada)} (visible ~{estado.latencia_firms_h} h después)
                </p>
              </div>
            </div>
          )}
          {incendio && !pronostico && estado?.modo === "demo" && (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4">
              <p className="rounded-lg border bg-background/95 px-4 py-2 text-sm shadow-md">
                Foco de demostración sin pronóstico precalculado.
              </p>
            </div>
          )}
          {incendio && !pronostico && estado?.modo !== "demo" && incendio.actualizacion?.estado !== "fallido" && (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4">
              <p className="flex items-center gap-2 rounded-lg border bg-background/95 px-4 py-2 text-sm shadow-md">
                <LoaderCircle className="h-4 w-4 animate-spin text-amber-600" />
                Foco detectado. El pronóstico se está calculando.
              </p>
            </div>
          )}
          {incendio?.actualizacion?.estado === "fallido" && (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4">
              <p className="rounded-lg border border-amber-300 bg-amber-50/95 px-4 py-2 text-sm text-amber-950 shadow-md">
                Actualización demorada. Se mantiene el último pronóstico válido mientras el sistema reintenta.
              </p>
            </div>
          )}
          {cargando && (
            <p className="absolute right-3 top-3 flex items-center gap-1.5 rounded-md bg-background/90 px-2 py-1 text-xs shadow">
              <LoaderCircle className="h-3 w-3 animate-spin" /> Cargando pronóstico…
            </p>
          )}
        </div>
        {/* Outside the map so the basemap attribution never covers it. */}
        <p className="shrink-0 border-t bg-background px-3 py-1.5 text-center text-xs leading-snug text-foreground">
          Propagación potencial bajo condiciones modeladas, sin supresión ·{" "}
          <a href="/documentacion?tab=limites" className="underline underline-offset-2">Límites del modelo</a>.
        </p>
      </div>

      <aside
        className={cn(
          "flex max-h-[32dvh] w-full shrink-0 flex-col gap-4 overflow-auto border-t bg-background p-3 md:max-h-none md:w-80 md:border-l md:border-t-0 md:p-4",
          onElegir && !pronostico && "hidden",
        )}
      >
        {!onElegir && (
        <section>
          <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Incendios activos
          </h2>
          {!estado && <p className="mt-2 text-sm text-muted-foreground">Cargando…</p>}
          {estado && !incendios.length && (
            <p className="mt-2 text-sm text-muted-foreground">Ningún foco en el área en las últimas 24 h.</p>
          )}
          <ul className="mt-2 flex flex-col gap-1.5">
            {incendios.map((i) => (
              <li key={i.id}>
                <button
                  onClick={() => setElegido(i.id)}
                  className={cn(
                    "w-full rounded-md border px-3 py-2 text-left text-sm transition-colors",
                    i.id === incendio?.id ? "border-primary bg-primary/5" : "hover:bg-muted",
                  )}
                >
                  <span className="flex items-center gap-1.5 font-medium">
                    <Flame className="h-3.5 w-3.5 shrink-0 text-orange-600" /> {i.nombre.split(" · ")[0]}
                  </span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    {localTime(i.primera_deteccion)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        )}

        {pronostico && maxVisibleHorizon > 0 && (
          <>
            {!onElegir && <Separator />}
            <section aria-labelledby="prediction-horizon-label">
              <div className="flex items-center justify-between gap-3">
                <h2
                  id="prediction-horizon-label"
                  className="text-xs font-medium uppercase tracking-wide text-muted-foreground"
                >
                  Predicción hasta
                </h2>
                <output
                  htmlFor="prediction-horizon"
                  className="font-mono text-sm font-semibold tabular-nums text-foreground"
                >
                  {horizonte.toLocaleString("es", { maximumFractionDigits: 1 })} h
                </output>
              </div>
              <input
                id="prediction-horizon"
                type="range"
                min={Math.min(1, maxVisibleHorizon)}
                max={maxVisibleHorizon}
                step={1}
                value={horizonte}
                onChange={(event) => setVisibleHorizonHours(Number(event.target.value))}
                aria-label="Horizonte de predicción"
                className="mt-3 h-1 w-full cursor-pointer accent-orange-500"
              />
              <div className="mt-1 flex justify-between text-[10px] tabular-nums text-muted-foreground">
                <span>1 h</span>
                <span>{maxVisibleHorizon.toLocaleString("es")} h</span>
              </div>
            </section>
          </>
        )}

        {pronostico && (
          <section className="grid grid-cols-2 gap-4" aria-label="Pasadas satelitales">
            <div className="flex min-w-0 flex-col gap-1">
              <div className="flex items-center gap-1.5">
                <Satellite
                  className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
                <Tooltip content="Momento en que el satélite pasó por última vez sobre la región. Es la información más reciente que tenemos sobre dónde está quemando el incendio, y la predicción parte de ahí.">
                  <span className="text-xs text-muted-foreground">Última actualización</span>
                </Tooltip>
              </div>
              <div className="text-lg font-semibold leading-tight">
                {localTime(pronostico.pasada)}
              </div>
            </div>
            <div className="flex min-w-0 flex-col gap-1">
              <div className="flex items-center gap-1.5">
                <Satellite
                  className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
                <Tooltip content="Hora estimada en que el satélite volverá a pasar por la región. Cuando lo haga, se verá el estado real del incendio y la predicción se actualizará (los datos llegan unas horas después).">
                  <span className="text-xs text-muted-foreground">Próxima pasada</span>
                </Tooltip>
              </div>
              <div className="text-lg font-semibold leading-tight">
                {localTime(estado!.proxima_pasada_estimada)}
              </div>
            </div>
          </section>
        )}

        {pronostico && (
          <>
            <Separator />
            {windBand && (
              <>
                <section className="flex flex-col gap-2" aria-label="Meteorología">
                  <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Meteorología
                  </h2>
                  <p className="text-sm font-medium">
                    Viento {(windBand.speed_mph * MPH_TO_KMH).toLocaleString("es", { maximumFractionDigits: 1 })} km/h
                    hacia el {compassPoint(windBand.blows_to_deg)}
                  </p>
                  <div
                    className="h-1.5 rounded-full"
                    style={{ background: WIND_SPEED_GRADIENT }}
                    role="img"
                    aria-label="Escala de color de la velocidad del viento, de 0 a 64 km/h o más"
                  />
                  <div className="flex justify-between text-[10px] tabular-nums text-muted-foreground">
                    {WIND_SCALE_KMH.map((v, i) => (
                      <span key={v}>{v}{i === WIND_SCALE_KMH.length - 1 ? "+ km/h" : ""}</span>
                    ))}
                  </div>
                </section>
                <Separator />
              </>
            )}
            <FireGrowthStatsPanel
              timestamp={stamp}
              row={stats}
              observedAreaHa={observedAreaHa}
              predictedAreaHa={predictedAreaHa}
              horizonHours={horizonte}
            />
            {estado?.calcular_ensamble && (
              <>
                <Separator />
                <section className="flex flex-col gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={verAcuerdo} onChange={(e) => setVerAcuerdo(e.target.checked)} />
                    {ENSEMBLE_AGREEMENT_LAYER.name}
                  </label>
                  {verAcuerdo && acuerdo && <EnsembleAgreementLegend contract={acuerdo} />}
                  {verAcuerdo && acuerdoAviso && <p className="text-xs text-muted-foreground">{acuerdoAviso}</p>}
                </section>
              </>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
