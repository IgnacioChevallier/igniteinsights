"use client";

import { useEffect, useMemo, useState } from "react";
import { FireAnimationControls } from "@/components/fire-animation-controls";
import { FireMap, type ImageOverlay } from "@/components/fire-map";
import { Separator } from "@/components/ui/separator";
import { useFireClock } from "@/hooks/use-fire-clock";
import { formatArgentinaDateTime } from "@/lib/date-time";
import { snapToLevel, summarizeIsochrones } from "@/lib/isochrone-clock";
import { cn } from "@/lib/utils";

// Benchmark de validación (IGN-26 §Benchmark): incendio → protocolo → receta.
// Una receta es una versión del modelo; sólo se comparan recetas dentro de un protocolo.

type Metricas = {
  dice: number | null;
  iou: number | null;
  recall: number | null;
  precision: number | null;
  sesgo_area: number | null;
  alarma_sesgo: boolean;
  tp_ha: number;
  fp_ha: number;
  fn_ha: number;
};

type Principal = {
  referencia: string;
  ventana: number;
  dice: number | null;
  sesgo_area: number | null;
  alarma_sesgo: boolean;
  /** Dice en la hora t* en que lo predicho iguala el área observada: forma sin velocidad. */
  area_igualada?: { hora: number | null; alcanzada: boolean; dice: number | null };
} | null;

type Agregado = {
  incremento?: { recall: number | null; precision: number | null; dice: number | null };
  incremento_cercano?: { recall: number | null };
} | null;

type RecetaResumen = {
  receta: string;
  padre: string | null;
  motivo: string;
  factores: Record<string, string | number>;
  git: { sha: string; sucio: boolean };
  puntuada: boolean;
  principal: Principal;
  agregado_firms: Agregado;
};

type Protocolo = {
  protocolo: string;
  caso: string;
  descripcion: string;
  contiguo: boolean;
  referencias: string[];
  ventanas: { n: number; inicio: string; horas: number }[];
  recetas: RecetaResumen[];
};

type Incendio = { incendio: string; protocolos: Protocolo[] };
type LegendEntry = { code: number; label: string; color: string };

type Ventana = {
  n: number;
  inicio: string;
  horas: number;
  semilla_ha: number;
  predicho_ha: number;
  firms?: { incremento: Metricas; incremento_cercano?: Metricas };
  cicatriz?: { acumulado: Metricas };
  llegada?: { mediana_h: number | null; nunca_alcanzadas: number | null };
};

type Iteracion = {
  receta: string;
  linea_de_tiempo: boolean;
  ventanas: Ventana[];
  principal: Principal;
};

type Comparacion = {
  declarados: Record<string, [unknown, unknown]>;
  no_declarados: { ventana: number | null; insumo: string }[];
  codigo: [string, string] | null;
};

const ratio = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : v.toLocaleString("es", { maximumFractionDigits: 3 });
const hectares = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${v.toLocaleString("es", { maximumFractionDigits: 0 })} ha`;
const factores = (f: Record<string, string | number>) =>
  Object.entries(f).map(([k, v]) => `${k}=${v}`).join(" · ");

async function obtener<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  const envelope = await res.json();
  if (!res.ok || !envelope.data) {
    throw new Error(envelope.detail ?? envelope.error?.message ?? `Error ${res.status}`);
  }
  return envelope.data as T;
}

export function ValidationPanel() {
  const [incendios, setIncendios] = useState<Incendio[]>([]);
  const [leyenda, setLeyenda] = useState<LegendEntry[]>([]);
  const [incendioId, setIncendioId] = useState<string | null>(null);
  const [protocoloId, setProtocoloId] = useState<string | null>(null);
  const [recetaId, setRecetaId] = useState<string | null>(null);
  const [contraId, setContraId] = useState<string | null>(null);
  const [ventanaElegida, setVentanaElegida] = useState(0);
  const [iteracion, setIteracion] = useState<Iteracion | null>(null);
  const [isocronas, setIsocronas] = useState<GeoJSON.FeatureCollection | null>(null);
  const [overlay, setOverlay] = useState<ImageOverlay | null>(null);
  const [comparacion, setComparacion] = useState<Comparacion | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    obtener<{ fires: Incendio[]; legend: LegendEntry[] }>("/api/validation/fires")
      .then((data) => {
        setIncendios(data.fires);
        setLeyenda(data.legend);
        setIncendioId((actual) => actual ?? data.fires[0]?.incendio ?? null);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const incendio = incendios.find((i) => i.incendio === incendioId) ?? null;
  const protocolo =
    incendio?.protocolos.find((p) => p.protocolo === protocoloId) ??
    incendio?.protocolos.find((p) => p.recetas.some((r) => r.puntuada)) ??
    incendio?.protocolos[0] ??
    null;
  const puntuadas = useMemo(() => protocolo?.recetas.filter((r) => r.puntuada) ?? [], [protocolo]);
  // La receta elegida puede no existir en otro protocolo: se cae a la primera puntuada.
  const receta = puntuadas.find((r) => r.receta === recetaId) ?? puntuadas[0] ?? null;
  const base = protocolo && receta ? `/api/validation/iterations/${protocolo.caso}/${receta.receta}` : null;

  // Lo anterior queda en pantalla hasta que llega lo nuevo: vaciar las isócronas llevaría
  // el horizonte a 0 y el reloj perdería el instante al cambiar de receta.
  useEffect(() => {
    if (!base) return;
    setCargando(true);
    obtener<Iteracion>(base)
      .then(async (it) => {
        // Con una cadena en una sola grilla se anima toda; si no, ventana por ventana.
        const url = it.linea_de_tiempo ? `${base}/isochrones` : `${base}/isochrones?ventana=${ventanaElegida}`;
        const nuevas = await obtener<GeoJSON.FeatureCollection>(url);
        setIteracion(it);
        setIsocronas(nuevas);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setCargando(false));
  }, [base, ventanaElegida]);

  const resumen = useMemo(() => summarizeIsochrones(isocronas), [isocronas]);
  const clock = useFireClock({ horizonHours: resumen.timedCount > 0 ? resumen.horizonHours : 0 });
  const snappedT = snapToLevel(clock.t, resumen.levels);
  const clockView = useMemo(
    () => ({ t: snappedT, stepHours: resumen.stepHours, horizonHours: resumen.horizonHours }),
    [snappedT, resumen.stepHours, resumen.horizonHours],
  );

  // En una línea de tiempo cosida, la ventana es la que contiene al reloj.
  const inicioCaso = protocolo ? Date.parse(protocolo.ventanas[0].inicio) : 0;
  const desfases = useMemo(
    () => protocolo?.ventanas.map((v) => (Date.parse(v.inicio) - inicioCaso) / 3_600_000) ?? [],
    [protocolo, inicioCaso],
  );
  const ventanaActiva = iteracion?.linea_de_tiempo
    ? Math.max(0, desfases.findLastIndex((d) => d <= snappedT))
    : ventanaElegida;

  useEffect(() => {
    if (!base) return;
    obtener<ImageOverlay>(`${base}/windows/${ventanaActiva}/overlay`)
      .then(setOverlay)
      .catch(() => setOverlay(null));
  }, [base, ventanaActiva]);

  useEffect(() => {
    setComparacion(null);
    if (!protocolo || !receta || !contraId || contraId === receta.receta) return;
    const a = `${protocolo.caso}/${receta.receta}`;
    const b = `${protocolo.caso}/${contraId}`;
    obtener<Comparacion>(`/api/validation/compare?a=${a}&b=${b}`)
      .then(setComparacion)
      .catch((e: Error) => setError(e.message));
  }, [protocolo, receta, contraId]);

  const inicioReloj = iteracion?.linea_de_tiempo
    ? protocolo?.ventanas[0].inicio
    : protocolo?.ventanas[ventanaElegida]?.inicio;
  const animable = resumen.timedCount > 0 && resumen.horizonHours > 0;

  return (
    <div className="flex h-full">
      <div className="relative min-h-0 flex-1">
        <FireMap
          isochrones={isocronas}
          fitTo={isocronas}
          fuelsOverlay={overlay}
          clock={animable ? clockView : null}
          overlay={
            animable ? (
              <div className="flex flex-col gap-1">
                <FireAnimationControls clock={clock} ignitionDatetime={inicioReloj ?? null} />
                {iteracion?.linea_de_tiempo && (
                  <div className="flex flex-wrap gap-1" aria-label="Ventanas de la cadena">
                    {desfases.map((d, n) => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => clock.seek(d)}
                        className={cn(
                          "rounded border bg-card/95 px-1.5 py-0.5 text-[10px] shadow-sm",
                          n === ventanaActiva && "bg-primary text-primary-foreground",
                        )}
                      >
                        Ventana {n}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : null
          }
        />
      </div>

      <aside className="flex w-96 shrink-0 flex-col gap-3 overflow-auto border-l bg-background p-3">
        <div>
          <h2 className="text-sm font-medium">Validación</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Cada receta es una versión del modelo, corrida sobre un caso congelado. Se
            puntúa lo que el modelo agregó, nunca lo que ya estaba quemado al empezar.
          </p>
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}
        {!error && incendios.length === 0 && (
          <p className="text-xs text-muted-foreground">Cargando incendios…</p>
        )}

        {incendio && protocolo && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <label className="text-xs font-medium">
                Incendio
                <select
                  className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-xs"
                  value={incendio.incendio}
                  onChange={(e) => {
                    setIncendioId(e.target.value);
                    setProtocoloId(null);
                    setVentanaElegida(0);
                  }}
                >
                  {incendios.map((i) => (
                    <option key={i.incendio} value={i.incendio}>{i.incendio}</option>
                  ))}
                </select>
              </label>
              <label className="text-xs font-medium">
                Protocolo
                <select
                  className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-xs"
                  value={protocolo.protocolo}
                  onChange={(e) => {
                    setProtocoloId(e.target.value);
                    setVentanaElegida(0);
                  }}
                >
                  {incendio.protocolos.map((p) => (
                    <option key={p.protocolo} value={p.protocolo}>{p.protocolo}</option>
                  ))}
                </select>
              </label>
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">{protocolo.descripcion}</p>

            <div>
              <h3 className="text-xs font-medium">Recetas</h3>
              {puntuadas.length === 0 && (
                <p className="mt-1 text-[11px] text-muted-foreground">Ninguna receta puntuada todavía.</p>
              )}
              <ul className="mt-1 flex flex-col gap-1">
                {puntuadas.map((r) => (
                  <li key={r.receta}>
                    <button
                      type="button"
                      onClick={() => setRecetaId(r.receta)}
                      className={cn(
                        "w-full rounded-md border px-2 py-1.5 text-left text-xs transition-colors",
                        receta?.receta === r.receta ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                      )}
                    >
                      <div className="flex justify-between gap-2 font-medium">
                        <span>{r.receta}</span>
                        <span className="tabular-nums">
                          {r.principal?.referencia === "cicatriz"
                            ? `Dice ${ratio(r.principal.dice)} · sesgo ${ratio(r.principal.sesgo_area)}×${r.principal.alarma_sesgo ? " ⚠" : ""}`
                            : `Dice FIRMS ${ratio(r.principal?.dice)}`}
                        </span>
                      </div>
                      <div className="mt-0.5 text-[10px] opacity-80">{factores(r.factores)}</div>
                      {r.principal?.area_igualada?.hora != null && (
                        <div className="mt-0.5 text-[10px] tabular-nums opacity-80">
                          forma {ratio(r.principal.area_igualada.dice)} · alcanza el área{" "}
                          {r.principal.area_igualada.alcanzada
                            ? `a las ${Math.round(r.principal.area_igualada.hora)} h`
                            : "no llega"}
                        </div>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
              {receta && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {receta.padre ? `Padre: ${receta.padre}. ` : ""}
                  {receta.motivo}
                  {receta.git.sucio && " · corrida con cambios sin commitear"}
                </p>
              )}
            </div>

            {!iteracion?.linea_de_tiempo && protocolo.ventanas.length > 1 && (
              <label className="text-xs font-medium">
                Ventana
                <select
                  className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-xs"
                  value={ventanaElegida}
                  onChange={(e) => setVentanaElegida(Number(e.target.value))}
                >
                  {protocolo.ventanas.map((v) => (
                    <option key={v.n} value={v.n}>
                      {v.n} · {formatArgentinaDateTime(v.inicio)} · {v.horas} h
                    </option>
                  ))}
                </select>
              </label>
            )}

            {cargando && (
              <p className="text-[11px] text-muted-foreground">Cargando la animación…</p>
            )}

            <Separator />

            <ul className="flex flex-col gap-1.5">
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

            <Separator />

            {iteracion && (
              <div>
                <h3 className="text-xs font-medium">Por ventana</h3>
                <table className="mt-2 w-full text-[11px] tabular-nums">
                  <thead className="text-muted-foreground">
                    <tr>
                      <th className="text-left font-medium">#</th>
                      <th className="text-right font-medium">Agregó</th>
                      <th className="text-right font-medium" title="Contra las detecciones nuevas de la ventana">
                        Recall F
                      </th>
                      <th className="text-right font-medium" title="Cota: un hueco del satélite no es un error">
                        Prec. F
                      </th>
                      <th className="text-right font-medium" title="Contra la cicatriz, acumulado">Dice C</th>
                      <th className="text-right font-medium">Sesgo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {iteracion.ventanas.map((v) => {
                      const c = v.cicatriz?.acumulado;
                      return (
                        <tr key={v.n} className={cn(v.n === ventanaActiva && "font-medium text-foreground")}>
                          <td className="text-left">{v.n}</td>
                          <td className="text-right">{hectares(v.predicho_ha)}</td>
                          <td className="text-right">{ratio(v.firms?.incremento.recall)}</td>
                          <td className="text-right">{ratio(v.firms?.incremento.precision)}</td>
                          <td className="text-right">{ratio(c?.dice)}</td>
                          <td className={cn("text-right", c?.alarma_sesgo && "text-amber-700 dark:text-amber-400")}>
                            {c ? `${ratio(c.sesgo_area)}×` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {puntuadas.length > 1 && receta && (
              <>
                <Separator />
                <div>
                  <label className="text-xs font-medium">
                    Comparar con
                    <select
                      className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-xs"
                      value={contraId ?? ""}
                      onChange={(e) => setContraId(e.target.value || null)}
                    >
                      <option value="">—</option>
                      {puntuadas
                        .filter((r) => r.receta !== receta.receta)
                        .map((r) => (
                          <option key={r.receta} value={r.receta}>{r.receta}</option>
                        ))}
                    </select>
                  </label>
                  {comparacion && (
                    <div className="mt-2 flex flex-col gap-1 text-[11px]">
                      {Object.entries(comparacion.declarados).map(([k, [a, b]]) => (
                        <div key={k}>
                          Declarado: <span className="font-medium">{k}</span> {String(a)} → {String(b)}
                        </div>
                      ))}
                      {comparacion.no_declarados.length > 0 ? (
                        <div className="text-amber-700 dark:text-amber-400">
                          Cambios NO declarados:{" "}
                          {comparacion.no_declarados
                            .map((x) => `${x.insumo}${x.ventana === null ? "" : ` (v${x.ventana})`}`)
                            .join(", ")}
                        </div>
                      ) : (
                        <div className="text-muted-foreground">Ningún cambio sin declarar en los insumos.</div>
                      )}
                      {comparacion.codigo && (
                        <div className="text-muted-foreground">
                          Código distinto: {comparacion.codigo[0].slice(0, 7)} → {comparacion.codigo[1].slice(0, 7)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
