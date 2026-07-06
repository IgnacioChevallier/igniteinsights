"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

const SETTINGS_KEY = "igniteinsights.settings";

export type IngestionSettings = {
  include_firms: boolean;
  include_dem: boolean;
  include_gfs: boolean;
  include_worldcover: boolean;
  include_canopy: boolean;
  firms_day_range: number;
  firms_start_date: string;
};

export const DEFAULT_SETTINGS: IngestionSettings = {
  include_firms: true,
  include_dem: false,
  include_gfs: true,
  include_worldcover: false,
  include_canopy: false,
  firms_day_range: 1,
  firms_start_date: "",
};

export function loadSettings(): IngestionSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {}
  return DEFAULT_SETTINGS;
}

export function saveSettings(s: IngestionSettings) {
  if (typeof window === "undefined") return;
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

type Status = "idle" | "running" | "success" | "error";
type Phase = "ingesting" | "simulating" | null;

// Errors come back in two shapes: FastAPI's raw HTTPException body ({ detail })
// for validation/failure responses, or this API's own success/partial-failure
// envelope ({ status, error }) where `error` may be a string or a per-source
// error map. Normalize both into a single readable string.
function extractErrorMessage(envelope: Record<string, unknown>, statusCode: number): string {
  if (typeof envelope.detail === "string") return envelope.detail;
  if (typeof envelope.error === "string") return envelope.error;
  if (envelope.error && typeof envelope.error === "object") {
    const values = Object.values(envelope.error as Record<string, unknown>).filter(Boolean);
    if (values.length) return values.join("; ");
  }
  return `HTTP ${statusCode}`;
}

export function DashboardHeader({
  generatedAt,
  apiBaseUrl,
}: {
  generatedAt: string;
  apiBaseUrl: string;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [phase, setPhase] = useState<Phase>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [firmsLabel, setFirmsLabel] = useState<string | null>(null);

  useEffect(() => {
    const s = loadSettings();
    if (!s.include_firms) {
      setFirmsLabel(null);
      return;
    }
    const range = `${s.firms_day_range} ${s.firms_day_range === 1 ? "día" : "días"}`;
    setFirmsLabel(
      s.firms_start_date
        ? `FIRMS: desde ${s.firms_start_date} · ${range}`
        : `FIRMS: últimos ${range}`,
    );
  }, []);

  async function handleRun() {
    setStatus("running");
    setErrorDetail(null);
    if (resetTimer.current) clearTimeout(resetTimer.current);

    const s = loadSettings();
    const body: Record<string, unknown> = {
      include_firms: s.include_firms,
      include_dem: s.include_dem,
      include_gfs: s.include_gfs,
      include_worldcover: s.include_worldcover,
      include_canopy: s.include_canopy,
      firms_day_range: s.firms_day_range,
    };
    if (s.firms_start_date) body.firms_start_date = s.firms_start_date;

    try {
      setPhase("ingesting");
      const res = await fetch("/api/ingestion/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const envelope = await res.json();
      if (!res.ok || (envelope.status && envelope.status !== "success")) {
        throw new Error(
          `Falló la ingesta: ${extractErrorMessage(envelope, res.status)}`
        );
      }

      const inputsDir = envelope.data?.preparation?.inputs_dir;
      const ignitionDatetime = envelope.data?.preparation?.ignition_datetime;
      if (inputsDir) {
        setPhase("simulating");
        const simRes = await fetch("/api/simulations/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            inputs_dir: inputsDir,
            ...(ignitionDatetime ? { ignition_datetime: ignitionDatetime } : {}),
          }),
        });
        const simEnvelope = await simRes.json();
        if (!simRes.ok || (simEnvelope.status && simEnvelope.status !== "success")) {
          throw new Error(
            `Falló la simulación: ${extractErrorMessage(simEnvelope, simRes.status)}`
          );
        }
      }

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
      <div>
        <h1 className="text-2xl font-semibold">Ignite Insights</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Generado {generatedAt} · {apiBaseUrl}
        </p>
        {firmsLabel && (
          <p className="mt-0.5 text-xs text-muted-foreground">{firmsLabel}</p>
        )}
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
