"use client";

import { useState } from "react";
import { ClientHeader } from "@/components/client-header";
import { ClientMap } from "@/components/client-map";
import { useEstado } from "@/lib/operativo";

export function ClientHome({ isAdmin = false }: { isAdmin?: boolean }) {
  const { estado, error } = useEstado();
  const [elegido, setElegido] = useState<string | null>(null);
  return (
    <div className="flex h-screen flex-col">
      <ClientHeader active="mapa" isAdmin={isAdmin} elegido={elegido} onElegir={setElegido} />
      {error && !estado && (
        <p role="alert" className="px-4 py-2 text-sm text-destructive">
          No se pudo leer el estado del sistema ({error}). Se reintenta cada minuto.
        </p>
      )}
      <div className="min-h-0 flex-1">
        <ClientMap estado={estado} elegido={elegido} onElegir={setElegido} />
      </div>
    </div>
  );
}
