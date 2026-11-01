"use client";

import { useCallback, useEffect, useState } from "react";

/** GET /api/v1/operativo/estado — app/operativo/servicio.py `estado`. */
export type Pronostico = {
  id: string;
  simulacion_id: string | null;
  pasada: string;
  disponible: string;
  ciclo_gfs: string | null;
  /** Whether this run has ensemble_agreement.json: the ensemble is not computed on every pass. */
  ensamble: boolean;
};

export type Incendio = {
  id: string;
  nombre: string;
  primera_deteccion: string;
  ultima_deteccion: string;
  detecciones: number;
  bbox: [number, number, number, number];
  pronostico: Pronostico | null;
  actualizacion: { estado: "corriendo" | "listo" | "fallido"; pasada: string; error: string | null } | null;
};

export type Estado = {
  modo: "demo" | "vivo";
  ahora: string;
  latencia_firms_h: number;
  calcular_ensamble: boolean;
  ultima_pasada: string | null;
  proxima_pasada_estimada: string;
  horizonte_h: number;
  incendios: Incendio[];
  detecciones: GeoJSON.FeatureCollection;
};

export const ESTADO_URL = "/api/v1/operativo/estado";

/** The state every client view reads, refreshed every `pollMs` (the cron runs every 30 min). */
export function useEstado(pollMs = 60_000) {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const res = await fetch(ESTADO_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEstado((await res.json()).data as Estado);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    }
  }, []);

  useEffect(() => {
    void reload();
    const id = setInterval(() => void reload(), pollMs);
    return () => clearInterval(id);
  }, [reload, pollMs]);

  return { estado, error, reload, setEstado };
}
