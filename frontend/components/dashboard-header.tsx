"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
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

        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/settings")}
          aria-label="Configuración"
        >
          <SettingsIcon />
        </Button>
      </div>
    </header>
  );
}

function SettingsIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
