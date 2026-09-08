"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { SettingsButton } from "@/components/settings-button";
import {
  describeSettings,
  loadSettings,
  runRealSimulation,
  type RunPhase,
} from "@/lib/real-run";

type Status = "idle" | "running" | "success" | "error";

export function DashboardHeader({
  generatedAt,
  apiBaseUrl,
}: {
  generatedAt: string;
  apiBaseUrl: string;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [phase, setPhase] = useState<RunPhase>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // localStorage is not readable while rendering on the server, so this waits for mount.
  const [firmsLabel, setFirmsLabel] = useState<string | null>(null);

  useEffect(() => {
    setFirmsLabel(describeSettings(loadSettings())[0] ?? null);
  }, []);

  async function handleRun() {
    setStatus("running");
    setErrorDetail(null);
    if (resetTimer.current) clearTimeout(resetTimer.current);

    try {
      await runRealSimulation(loadSettings(), setPhase);
      setStatus("success");
      router.refresh();
    } catch (err) {
      setStatus("error");
      setErrorDetail(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setPhase(null);
    }

    resetTimer.current = setTimeout(() => {
      setStatus("idle");
      setErrorDetail(null);
    }, 5000);
  }

  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <img
          src="/images/wildfire-logo-tree-colored.svg"
          alt=""
          aria-hidden="true"
          className="mt-0.5 h-8 w-8 shrink-0"
        />
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold leading-tight">Ignite Insights</h1>
          <p className="mt-1 break-words text-sm text-muted-foreground">
            Generado {generatedAt} · {apiBaseUrl}
          </p>
          {firmsLabel && (
            <p className="mt-0.5 text-xs text-muted-foreground">{firmsLabel}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {status === "success" && (
          <span className="text-xs text-green-600">Ingesta + simulación iniciadas ✓</span>
        )}
        {status === "error" && (
          <span className="text-xs text-destructive">
            {errorDetail ?? "Falló la ejecución"} ✗
          </span>
        )}

        <Button size="sm" onClick={handleRun} disabled={status === "running"}>
          {status === "running"
            ? phase === "simulating"
              ? "Simulando..."
              : "Ingestando..."
            : "Ejecutar"}
        </Button>

        <form>
          <Button type="submit" variant="outline" size="sm">
            Actualizar
          </Button>
        </form>

        <SettingsButton />
      </div>
    </header>
  );
}
