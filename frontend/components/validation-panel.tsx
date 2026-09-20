"use client";

import { useEffect, useMemo, useState } from "react";
import { FireMap, type ImageOverlay } from "@/components/fire-map";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

// GET /api/validation/cases — lo que cada mapa de combustible predijo contra lo observado.
type Metrics = {
  mapa: string;
  iou: number | null;
  recall: number | null;
  precision: number | null;
  recall_cercano?: number | null;
  tp_ha?: number;
  fp_ha?: number;
  fn_ha?: number;
  acierto_ha?: number;
  sin_deteccion_ha?: number;
  no_predicho_ha?: number;
};

type Caso = {
  id: string;
  harness: string;
  harness_label: string;
  referencia: string;
  caso: string;
  meta: Record<string, unknown>;
  mapas: Record<string, Metrics>;
};

type LegendEntry = { code: number; label: string; color: string };

const MAPAS = ["worldcover", "mapbiomas", "ccsbap"] as const;
const ETIQUETAS: Record<string, string> = {
  worldcover: "WorldCover",
  mapbiomas: "MapBiomas",
  ccsbap: "CCS-BAP",
};

const ratio = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : v.toLocaleString("es", { maximumFractionDigits: 3 });

const hectares = (v: number | null | undefined) =>
  v === null || v === undefined
    ? "—"
    : `${v.toLocaleString("es", { maximumFractionDigits: 0 })} ha`;

/** Hectáreas por categoría, con los nombres distintos que usa cada harness. */
const areas = (m: Metrics) => ({
  acierto: m.tp_ha ?? m.acierto_ha,
  sinObservacion: m.fp_ha ?? m.sin_deteccion_ha,
  noPredicho: m.fn_ha ?? m.no_predicho_ha,
});

export function ValidationPanel() {
  const [casos, setCasos] = useState<Caso[]>([]);
  const [leyenda, setLeyenda] = useState<LegendEntry[]>([]);
  const [casoId, setCasoId] = useState<string | null>(null);
  const [mapa, setMapa] = useState<string>("ccsbap");
  const [overlay, setOverlay] = useState<ImageOverlay | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/validation/cases", { cache: "no-store" })
      .then(async (res) => {
        const envelope = await res.json();
        if (!res.ok || !envelope.data) {
          throw new Error(envelope.detail ?? envelope.error?.message ?? "Sin datos");
        }
        setCasos(envelope.data.cases as Caso[]);
        setLeyenda(envelope.data.legend as LegendEntry[]);
        setCasoId((actual) => actual ?? (envelope.data.cases[0]?.id ?? null));
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const caso = useMemo(
    () => casos.find((c) => c.id === casoId) ?? null,
    [casos, casoId],
  );

  // El mapa elegido puede no estar puntuado todavía en este caso: se cae al primero que sí.
  const mapaActivo = useMemo(() => {
    if (!caso) return mapa;
    return caso.mapas[mapa] ? mapa : Object.keys(caso.mapas)[0];
  }, [caso, mapa]);

  useEffect(() => {
    if (!caso || !mapaActivo) return;
    setOverlay(null);
    const [harness, nombre] = caso.id.split("/");
    fetch(
      `/api/validation/overlay?harness=${harness}&caso=${nombre}&mapa=${mapaActivo}`,
      { cache: "no-store" },
    )
      .then(async (res) => {
        const envelope = await res.json();
        if (!res.ok || !envelope.data) {
          throw new Error(envelope.detail ?? "No se pudo cargar la capa");
        }
        setOverlay(envelope.data as ImageOverlay);
      })
      .catch((e: Error) => setError(e.message));
  }, [caso, mapaActivo]);

  return (
    <div className="flex h-full">
      <div className="relative min-h-0 flex-1">
        <FireMap fuelsOverlay={overlay} />
      </div>

      <aside className="flex w-96 shrink-0 flex-col gap-3 overflow-auto border-l bg-background p-3">
        <div>
          <h2 className="text-sm font-medium">Validación</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Qué predijo cada mapa de combustible contra lo que efectivamente se quemó.
            Se puntúa sólo el anillo de crecimiento: la semilla coincide por construcción
            y puntuarla infla el resultado sin medir nada del modelo.
          </p>
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}
        {!error && casos.length === 0 && (
          <p className="text-xs text-muted-foreground">Cargando casos…</p>
        )}

        {casos.length > 0 && (
          <>
            <div>
              <label className="text-xs font-medium" htmlFor="caso">
                Caso
              </label>
              <select
                id="caso"
                className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-xs"
                value={casoId ?? ""}
                onChange={(e) => setCasoId(e.target.value)}
              >
                {casos.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.harness_label} · {c.caso}
                  </option>
                ))}
              </select>
              {caso && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Referencia: {caso.referencia}
                </p>
              )}
            </div>

            <div className="flex gap-1">
              {MAPAS.filter((m) => caso?.mapas[m]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMapa(m)}
                  className={cn(
                    "flex-1 rounded-md border px-2 py-1.5 text-xs font-medium transition-colors",
                    mapaActivo === m
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted",
                  )}
                >
                  {ETIQUETAS[m]}
                </button>
              ))}
            </div>

            <Separator />

            <div>
              <h3 className="text-xs font-medium">Qué muestra el mapa</h3>
              <ul className="mt-2 flex flex-col gap-1.5">
                {leyenda.map((l) => (
                  <li key={l.code} className="flex items-center gap-2 text-xs">
                    <span
                      className="inline-block h-3 w-3 shrink-0 rounded-sm border"
                      style={{ backgroundColor: l.color }}
                    />
                    <span>{l.label}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Separator />

            {caso && (
              <div>
                <h3 className="text-xs font-medium">Los tres mapas en este caso</h3>
                <table className="mt-2 w-full text-[11px] tabular-nums">
                  <thead className="text-muted-foreground">
                    <tr>
                      <th className="text-left font-medium">Mapa</th>
                      <th className="text-right font-medium">IoU</th>
                      <th className="text-right font-medium">Recall</th>
                      <th className="text-right font-medium">Precisión</th>
                    </tr>
                  </thead>
                  <tbody>
                    {MAPAS.filter((m) => caso.mapas[m]).map((m) => {
                      const met = caso.mapas[m];
                      return (
                        <tr
                          key={m}
                          className={cn(mapaActivo === m && "font-medium text-foreground")}
                        >
                          <td className="text-left">{ETIQUETAS[m]}</td>
                          <td className="text-right">{ratio(met.iou)}</td>
                          <td className="text-right">
                            {ratio(met.recall_cercano ?? met.recall)}
                          </td>
                          <td className="text-right">{ratio(met.precision)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {caso.mapas[mapaActivo] && (
                  <ul className="mt-3 flex flex-col gap-1 text-[11px] text-muted-foreground">
                    <li>Acierto: {hectares(areas(caso.mapas[mapaActivo]).acierto)}</li>
                    <li>
                      Predicho sin observación:{" "}
                      {hectares(areas(caso.mapas[mapaActivo]).sinObservacion)}
                    </li>
                    <li>
                      Observado y no predicho:{" "}
                      {hectares(areas(caso.mapas[mapaActivo]).noPredicho)}
                    </li>
                  </ul>
                )}
              </div>
            )}

            <Separator />

            <p className="text-[11px] leading-relaxed text-muted-foreground">
              {caso?.harness === "harness_a"
                ? "El recall que se muestra está restringido a lo alcanzable por el frente en 24 h: las detecciones lejos de lo que ya ardía son igniciones nuevas, y un modelo de propagación no predice dónde se inicia un foco. La precisión es una cota inferior, porque una celda predicha sin detección puede ser un hueco del satélite."
                : "La referencia es la cicatriz final de semanas y la corrida es de 12 h, así que el recall está acotado por construcción: lo comparable entre mapas es el orden, no la magnitud."}
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
