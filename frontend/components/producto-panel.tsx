"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { ClientMap } from "@/components/client-map";
import { Button } from "@/components/ui/button";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";
import { useEstado, type Estado } from "@/lib/operativo";

async function send(url: string, method: "PUT" | "POST", body?: object): Promise<Estado> {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
  return json.data as Estado;
}

/**
 * The admin's side of the product: the controls that are ours (mode, the demo clock, whether
 * the ensemble is computed) above exactly the map a client sees. "Pasada siguiente" is how the
 * defence walks a past fire forward pass by pass, the way P-24 re-forecasts.
 */
export function ProductoPanel() {
  const { estado, setEstado } = useEstado();
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<Estado>) => {
    setError(null);
    try {
      setEstado(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-3 border-b bg-muted/40 px-4 py-2 text-sm">
        <label className="flex items-center gap-2">
          Modo
          <select
            className="h-8 rounded-md border border-input bg-background px-2 text-sm"
            value={estado?.modo ?? "demo"}
            onChange={(e) => run(() => send("/api/v1/operativo", "PUT", { modo: e.target.value }))}
          >
            <option value="demo">Demostración (reloj congelado)</option>
            <option value="vivo">En vivo</option>
          </select>
        </label>
        {estado?.modo === "demo" && (
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="outline"
              onClick={() => run(() => send("/api/v1/operativo/pasada?direccion=-1", "POST"))}
            >
              <ChevronLeft className="h-4 w-4" /> Pasada anterior
            </Button>
            <span className="tabular-nums">
              {formatArgentinaDateTime(estado.ahora)} {ARGENTINA_TIME_ZONE_LABEL}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => run(() => send("/api/v1/operativo/pasada?direccion=1", "POST"))}
            >
              Pasada siguiente <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={estado?.calcular_ensamble ?? false}
            onChange={(e) =>
              run(() => send("/api/v1/operativo", "PUT", { calcular_ensamble: e.target.checked }))
            }
          />
          Acuerdo del ensamble visible para clientes
        </label>
        {error && <span className="text-destructive">{error}</span>}
      </div>
      <div className="min-h-0 flex-1">
        <ClientMap estado={estado} />
      </div>
    </div>
  );
}
