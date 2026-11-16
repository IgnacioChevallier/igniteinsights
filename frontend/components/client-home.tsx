"use client";

import { useState } from "react";
import { ClientHeader } from "@/components/client-header";
import { ClientMap } from "@/components/client-map";
import { useEstado } from "@/lib/operativo";

export function ClientHome({ isAdmin = false, signedIn = true }: { isAdmin?: boolean; signedIn?: boolean }) {
  const { estado, error } = useEstado();
  const [elegido, setElegido] = useState<string | null>(null);
  return (
    // dvh, not vh: on mobile Safari 100vh runs under the browser toolbar and hid the footer.
    <div className="flex h-dvh flex-col">
      <ClientHeader active="mapa" isAdmin={isAdmin} signedIn={signedIn} elegido={elegido} onElegir={setElegido} />
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
