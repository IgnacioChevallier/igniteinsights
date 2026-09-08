/**
 * Launching a real simulation: ingest the live sources, prepare the ELMFIRE inputs from
 * them, then run ELMFIRE on the result.
 *
 * One implementation, two entry points — the header on the "Datos" section and the map's
 * own sidebar. It lived inside `dashboard-header.tsx` while that was the only caller;
 * having a second one is what moved it here rather than copying it.
 *
 * What gets ingested is whatever `/settings` saved. That page stays the single source of
 * truth, so a run launched from the map can never quietly pull something the settings say
 * it should not — the static layers in particular, where canopy alone is ~500 MB.
 */

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

/** What the next run will actually pull, in words. The map offers no toggles of its own,
 *  so this is the only way to see what the button is about to do before pressing it. */
export function describeSettings(s: IngestionSettings): string[] {
  const lines: string[] = [];
  if (s.include_firms) {
    const range = `${s.firms_day_range} ${s.firms_day_range === 1 ? "día" : "días"}`;
    lines.push(
      s.firms_start_date
        ? `Incendios FIRMS desde ${s.firms_start_date} · ${range}`
        : `Incendios FIRMS · últimos ${range}`,
    );
  }
  if (s.include_gfs) {
    // The ingestion endpoint derives the GFS date from the FIRMS window when one is set,
    // so a historical fire is never paired with today's weather. Say which it will be.
    lines.push(
      s.firms_start_date ? "Meteorología GFS del mismo período" : "Meteorología GFS · ciclo actual",
    );
  }
  const statics = [
    [s.include_dem, "relieve"],
    [s.include_worldcover, "combustibles"],
    [s.include_canopy, "dosel"],
  ] as const;
  const on = statics.filter(([v]) => v).map(([, name]) => name);
  const off = statics.filter(([v]) => !v).map(([, name]) => name);
  // Static layers are idempotent: already on disk means the run skips them. Saying so
  // stops "omitido" from reading as "this run has no terrain".
  if (on.length) lines.push(`${on.join(", ")} (se omiten si ya están descargados)`);
  if (off.length) lines.push(`Sin volver a pedir: ${off.join(", ")}`);
  return lines;
}

// Errors come back in two shapes: FastAPI's raw HTTPException body ({ detail })
// for validation/failure responses, or this API's own success/partial-failure
// envelope ({ status, error }) where `error` may be a string or a per-source
// error map. Normalize both into a single readable string.
export function extractErrorMessage(
  envelope: Record<string, unknown>,
  statusCode: number,
): string {
  if (typeof envelope.detail === "string") return envelope.detail;
  if (typeof envelope.error === "string") return envelope.error;
  if (envelope.error && typeof envelope.error === "object") {
    const values = Object.values(envelope.error as Record<string, unknown>).filter(Boolean);
    if (values.length) return values.join("; ");
  }
  return `HTTP ${statusCode}`;
}

export type RunPhase = "ingesting" | "simulating" | null;

/**
 * Ingest → prepare → simulate. Returns the new simulation id, or null when the ingestion
 * produced no inputs directory (nothing to simulate). Throws with a readable message on
 * either leg.
 *
 * Blocking and slow — minutes — because both legs are synchronous endpoints. `onPhase`
 * exists so the caller can say which leg is running instead of showing one long spinner.
 */
export async function runRealSimulation(
  settings: IngestionSettings,
  onPhase: (phase: RunPhase) => void,
): Promise<string | null> {
  const body: Record<string, unknown> = {
    include_firms: settings.include_firms,
    include_dem: settings.include_dem,
    include_gfs: settings.include_gfs,
    include_worldcover: settings.include_worldcover,
    include_canopy: settings.include_canopy,
    firms_day_range: settings.firms_day_range,
  };
  if (settings.firms_start_date) body.firms_start_date = settings.firms_start_date;

  onPhase("ingesting");
  const res = await fetch("/api/ingestion/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const envelope = await res.json();
  if (!res.ok || (envelope.status && envelope.status !== "success")) {
    throw new Error(`Falló la ingesta: ${extractErrorMessage(envelope, res.status)}`);
  }

  const inputsDir = envelope.data?.preparation?.inputs_dir;
  const ignitionDatetime = envelope.data?.preparation?.ignition_datetime;
  if (!inputsDir) return null;

  onPhase("simulating");
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
    throw new Error(`Falló la simulación: ${extractErrorMessage(simEnvelope, simRes.status)}`);
  }
  return (simEnvelope.data?.simulation_id as string) ?? null;
}
