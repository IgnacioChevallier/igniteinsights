"use client";

import { useEffect, useState } from "react";
import { FireMap, type ImageOverlay } from "@/components/fire-map";
import { Separator } from "@/components/ui/separator";

// GET /api/v1/fuels/map — the WorldCover → FBFM40 crosswalk currently in use.
type FuelClass = {
  fbfm40: number;
  label: string;
  color: string;
  source_classes: string[];
  pixel_count: number;
  area_ha: number;
  share: number;
};

type FuelsMap = ImageOverlay & {
  source: string;
  classes: FuelClass[];
  total_area_ha: number;
};

const percent = (share: number) =>
  share.toLocaleString("es", { style: "percent", maximumFractionDigits: 1 });

const hectares = (ha: number) =>
  `${ha.toLocaleString("es", { maximumFractionDigits: 0 })} ha`;

export function FuelsPanel() {
  const [fuels, setFuels] = useState<FuelsMap | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/fuels", { cache: "no-store" })
      .then(async (res) => {
        const envelope = await res.json();
        if (!res.ok || !envelope.data) {
          throw new Error(envelope.detail ?? envelope.error?.message ?? "Sin datos");
        }
        setFuels(envelope.data as FuelsMap);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="flex h-full">
      <div className="relative min-h-0 flex-1">
        <FireMap fuelsOverlay={fuels} />
      </div>

      <aside className="flex w-80 shrink-0 flex-col gap-3 overflow-auto border-l bg-background p-3">
        <div>
          <h2 className="text-sm font-medium">Modelo de combustible actual</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {fuels?.source ?? "ESA WorldCover → Scott & Burgan FBFM40"}
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
              Área total: {hectares(fuels.total_area_ha)}. Cada clase WorldCover se
              asigna a un único modelo FBFM40 — no hay diferenciación por especie
              dentro de la cobertura arbórea (lenga, coihue, ciprés y alerce comparten
              TL3). NB9 (99) es el valor sin dato: se contabiliza pero se dibuja
              transparente.
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
