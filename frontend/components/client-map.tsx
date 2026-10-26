"use client";

import { useEffect, useMemo, useState } from "react";
import { Flame, LoaderCircle, Satellite } from "lucide-react";
import { EnsembleAgreementLegend } from "@/components/ensemble-agreement-legend";
import { FireAnimationControls } from "@/components/fire-animation-controls";
import { FireGrowthStatsPanel, type FireSizeStatsRow } from "@/components/fire-growth-stats-panel";
import { FireMap } from "@/components/fire-map";
import type { WindFieldResponse } from "@/components/map-panel";
import { Separator } from "@/components/ui/separator";
import { useFireClock } from "@/hooks/use-fire-clock";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";
import {
  checkEnsembleAgreement,
  ENSEMBLE_AGREEMENT_LAYER,
  type EnsembleAgreementContract,
} from "@/lib/ensemble-agreement";
import { snapToLevel, summarizeIsochrones } from "@/lib/isochrone-clock";
import type { Estado, Incendio } from "@/lib/operativo";
import { cn } from "@/lib/utils";
import type { GriddedWindField } from "@/lib/wind-particles";

const art = (value: string) => `${formatArgentinaDateTime(value)} ${ARGENTINA_TIME_ZONE_LABEL}`;

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
 * in the next 24 h. Observed detections, the forecast isochrones from the last VIIRS pass,
 * wind and the 3D relief; the ensemble agreement only on request. Nothing here starts a
 * computation — the admin decides what is computed, the client only what to look at.
 */
export function ClientMap({ estado }: { estado: Estado | null }) {
  const [elegido, setElegido] = useState<string | null>(null);
  const incendios = useMemo(() => estado?.incendios ?? [], [estado]);
  const incendio = incendios.find((i) => i.id === elegido) ?? incendios[0] ?? null;
  const simulacionId = incendio?.pronostico?.simulacion_id ?? null;

  const [isochrones, setIsochrones] = useState<GeoJSON.FeatureCollection | null>(null);
  const [perimetro, setPerimetro] = useState<GeoJSON.FeatureCollection | null>(null);
  const [stats, setStats] = useState<FireSizeStatsRow | null>(null);
  const [wind, setWind] = useState<WindFieldResponse | null>(null);
  const [cargando, setCargando] = useState(false);
  const [verViento, setVerViento] = useState(false);
  const [verAcuerdo, setVerAcuerdo] = useState(false);
  const [acuerdo, setAcuerdo] = useState<EnsembleAgreementContract | null>(null);
  const [acuerdoAviso, setAcuerdoAviso] = useState<string | null>(null);

  useEffect(() => {
    setIsochrones(null);
    setPerimetro(null);
    setStats(null);
    setWind(null);
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
    if (!verAcuerdo || !simulacionId || acuerdo || acuerdoAviso) return;
    void getData<unknown>(`/api/simulations/${simulacionId}/ensemble-agreement`).then((data) => {
      const checked = data ? checkEnsembleAgreement(data) : "Todavía no hay acuerdo del ensamble para este pronóstico.";
      if (typeof checked === "string") setAcuerdoAviso(checked);
      else setAcuerdo(checked);
    });
  }, [verAcuerdo, simulacionId, acuerdo, acuerdoAviso]);

  const summary = useMemo(() => summarizeIsochrones(isochrones), [isochrones]);
  const horizonte = summary.horizonHours || estado?.horizonte_h || 0;
  const animable = summary.timedCount > 0 && horizonte > 0;
  const clock = useFireClock({ horizonHours: animable ? horizonte : 0 });
  const snappedT = snapToLevel(clock.t, summary.levels);
  const clockView = useMemo(
    () => ({ t: snappedT, stepHours: summary.stepHours, horizonHours: horizonte }),
    [snappedT, summary.stepHours, horizonte],
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

  return (
    <div className="flex h-full min-h-0 flex-col md:flex-row">
      <div className="flex min-h-[60vh] flex-1 flex-col md:min-h-0">
        <div className="relative min-h-0 flex-1">
          <FireMap
            activeFires={estado?.detecciones ?? null}
            isochrones={isochrones}
            ignitionPerimeter={perimetro}
            ensembleAgreement={verAcuerdo ? acuerdo : null}
            fitTo={encuadre}
            windField={windField}
            windTimeHours={clock.t}
            windSurfaceVisible={verViento}
            clock={animable ? clockView : null}
            overlay={
              animable ? (
                <FireAnimationControls clock={clock} ignitionDatetime={pronostico?.pasada ?? null} />
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
          {incendio && !pronostico && incendio.actualizacion?.estado !== "fallido" && (
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
          Propagación potencial bajo condiciones modeladas, sin supresión
          {pronostico
            ? ` · próximas ${estado?.horizonte_h ?? 24} h desde la pasada VIIRS de las ${art(pronostico.pasada)} (disponible ${art(pronostico.disponible)})`
            : ""}
          . <a href="/documentacion" className="underline underline-offset-2">Límites del modelo</a>
        </p>
      </div>

      <aside className="flex w-full shrink-0 flex-col gap-4 overflow-auto border-t bg-background p-4 md:w-80 md:border-l md:border-t-0">
        <section>
          <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {incendios.length === 1 ? "Incendio activo" : `Incendios activos (${incendios.length})`}
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
                    Primera detección {art(i.primera_deteccion)} · {i.detecciones} detecciones
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        {pronostico && (
          <section className="rounded-md border p-3 text-xs leading-relaxed">
            <p className="flex items-center gap-1.5 font-medium text-foreground">
              <Satellite className="h-3.5 w-3.5" /> Pasada VIIRS {art(pronostico.pasada)}
            </p>
            <p className="text-muted-foreground">
              Publicada en FIRMS ~{art(pronostico.disponible)}. Meteorología: pronóstico GFS del ciclo{" "}
              {pronostico.ciclo_gfs ? art(pronostico.ciclo_gfs) : "—"}.
            </p>
            <p className="mt-1 text-muted-foreground">
              Próxima pasada estimada ~{art(estado!.proxima_pasada_estimada)}.
            </p>
          </section>
        )}

        {pronostico && (
          <>
            <Separator />
            <section className="flex flex-col gap-2">
              <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Capas</h2>
              {wind && (
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={verViento} onChange={(e) => setVerViento(e.target.checked)} />
                  Velocidad del viento
                </label>
              )}
              {estado?.calcular_ensamble && (
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={verAcuerdo} onChange={(e) => setVerAcuerdo(e.target.checked)} />
                  {ENSEMBLE_AGREEMENT_LAYER.name}
                </label>
              )}
              {verAcuerdo && acuerdo && <EnsembleAgreementLegend contract={acuerdo} />}
              {verAcuerdo && acuerdoAviso && <p className="text-xs text-muted-foreground">{acuerdoAviso}</p>}
              <p className="text-[11px] text-muted-foreground">El botón 3D del mapa muestra el relieve.</p>
            </section>
            <Separator />
            <FireGrowthStatsPanel row={stats} />
          </>
        )}
      </aside>
    </div>
  );
}
