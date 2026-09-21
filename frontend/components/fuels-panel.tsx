"use client";

import { useEffect, useState } from "react";
import { FireMap } from "@/components/fire-map";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { loadFuelsMap, type FuelsMap } from "@/lib/fuels-cache";
import { FUELS_SOURCES, loadSettings, type FuelsSource } from "@/lib/real-run";

// GET /api/v1/fuels/map?source= — one cover product's FBFM40 map, as ELMFIRE receives it.

// Only WorldCover's caveat is about the crosswalk's resolution; the Argentine maps are the
// answer to it, so they point to the document that argues each assignment instead.
const SOURCE_NOTES: Record<FuelsSource, string> = {
  ccsbap:
    "Crosswalk nivel 3 de CCS-BAP con diferenciación por especie — ver IGN-20B-CROSSWALK-CCSBAP.md. El hueco fronterizo se rellena con WorldCover.",
  mapbiomas:
    "Crosswalk de MapBiomas Argentina Col. 2 — ver IGN-20-CROSSWALK.md. El hueco fronterizo se rellena con WorldCover.",
  worldcover:
    "Cada clase WorldCover se asigna a un único modelo FBFM40 — no hay diferenciación por especie dentro de la cobertura arbórea (lenga, coihue, ciprés y alerce comparten TL3).",
};

const percent = (share: number) =>
  share.toLocaleString("es", { style: "percent", maximumFractionDigits: 1 });

const hectares = (ha: number) =>
  `${ha.toLocaleString("es", { maximumFractionDigits: 0 })} ha`;

export function FuelsPanel() {
  const [source, setSource] = useState<FuelsSource | null>(null);
  const [available, setAvailable] = useState<FuelsSource[] | null>(null);
  const [fuels, setFuels] = useState<FuelsMap | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Start on the map the next run will use.
  useEffect(() => setSource(loadSettings().fuels_source), []);

  useEffect(() => {
    if (!source) return;
    let cancelled = false;
    setFuels(null);
    setError(null);
    loadFuelsMap(source)
      .then((data) => {
        if (cancelled) return;
        setFuels(data);
        setAvailable(data.available_sources);
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [source]);

  return (
    <div className="flex h-full">
      <div className="relative min-h-0 flex-1">
        <FireMap fuelsOverlay={fuels} />
      </div>

      <aside className="flex w-80 shrink-0 flex-col gap-3 overflow-auto border-l bg-background p-3">
        <div>
          <h2 className="text-sm font-medium">Mapa de combustibles</h2>
          <div className="mt-2 flex gap-1" role="group" aria-label="Fuente del mapa">
            {FUELS_SOURCES.map(({ id, label }) => {
              const built = available?.includes(id) ?? true;
              return (
                <Button
                  key={id}
                  size="sm"
                  variant={id === source ? "default" : "outline"}
                  className="h-7 flex-1 px-2 text-xs"
                  aria-pressed={id === source}
                  disabled={!built}
                  title={built ? undefined : "Sin construir: corré un run con esta fuente"}
                  onClick={() => setSource(id)}
                >
                  {label}
                </Button>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {fuels?.source ?? (source && FUELS_SOURCES.find((s) => s.id === source)?.description)}
          </p>
        </div>

        <Separator />

        {error && (
          <p className="text-xs text-destructive">
            No se pudo cargar el mapa de combustibles: {error}
          </p>
        )}
        {!error && !fuels && <p className="text-xs text-muted-foreground">Cargando…</p>}

        {fuels && (
          <>
            <ul className="flex flex-col gap-2">
              {fuels.classes.map((cls) => (
                <li key={cls.fbfm40} className="text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block h-3 w-3 shrink-0 rounded-sm border"
                      style={{ backgroundColor: cls.color }}
                    />
                    <span className="flex-1">{cls.label}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {percent(cls.share)}
                    </span>
                  </div>
                  <div className="mt-1 h-1 w-full rounded-full bg-muted">
                    <div
                      className="h-1 rounded-full"
                      style={{ width: `${cls.share * 100}%`, backgroundColor: cls.color }}
                    />
                  </div>
                  <div className="mt-1 pl-5 text-[11px] text-muted-foreground">
                    {cls.source_classes.join(" + ") || "sin clase de cobertura"} ·{" "}
                    {hectares(cls.area_ha)}
                  </div>
                </li>
              ))}
            </ul>

            <Separator />

            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Área total: {hectares(fuels.total_area_ha)}. {SOURCE_NOTES[fuels.source_id]}{" "}
              NB9 (99) es el valor sin dato: se contabiliza pero se dibuja transparente.
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
