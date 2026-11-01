import { CalendarClock, Flame, Radar, type LucideIcon } from "lucide-react";
import { Tooltip } from "@/components/ui/tooltip";

// One row per simulation run: ELMFIRE's final-state summary at tstop, not a time
// series (verified against real output CSVs — every run produces exactly one row).
// Crown fire area, fire volume, population affected, real estate value, PM2.5
// release, and peak HRR are all omitted here — either always structurally
// unavailable (no assets-at-risk/emissions pipeline exists) or dropped to keep
// this panel to the two figures that matter most in the narrow sidebar.
export type FireSizeStatsRow = {
  tstop_h: number | null;
  total_fire_area_ac: number | null;
};

const AC_TO_HA = 0.404686;

const TOOLTIPS = {
  timestamp: "Instante estimado (hora de Argentina) que muestra la animación del mapa.",
  observed:
    "Superficie del perímetro observado usado para iniciar la simulación. Corresponde a lo detectado hasta la última pasada satelital.",
  predicted:
    "Superficie total acumulada que alcanza el escenario modelado al final de la ventana seleccionada. Incluye el área observada inicial.",
};

function formatNumber(value: number | null, unit: string) {
  if (value === null) return "-";
  return `${value.toLocaleString("es", { maximumFractionDigits: 1 })} ${unit}`;
}

function StatRow({
  icon: Icon,
  label,
  value,
  tooltip,
  emphasized,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tooltip: string;
  emphasized?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <Tooltip content={tooltip}>
          <span className="text-xs text-muted-foreground">{label}</span>
        </Tooltip>
      </div>
      <div className={emphasized ? "text-xl font-semibold leading-tight" : "text-lg font-semibold leading-tight"}>
        {value}
      </div>
    </div>
  );
}

export function FireGrowthStatsPanel({
  row,
  observedAreaHa,
  predictedAreaHa,
  horizonHours,
  timestamp,
}: {
  /** Wall-clock time of the animation frame on screen, already formatted. */
  timestamp?: string | null;
  row: FireSizeStatsRow | null;
  observedAreaHa?: number | null;
  predictedAreaHa?: number | null;
  horizonHours?: number;
}) {
  const fallbackPrediction =
    row?.total_fire_area_ac !== null && row?.total_fire_area_ac !== undefined
      ? row.total_fire_area_ac * AC_TO_HA
      : null;
  const prediction = predictedAreaHa ?? fallbackPrediction;
  const predictionHorizon = horizonHours ?? row?.tstop_h ?? null;
  const hasArea = observedAreaHa != null || prediction != null;

  return (
    <div className="flex flex-col gap-3">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Resumen de crecimiento
      </div>
      {hasArea ? (
        <div className="flex flex-col gap-3">
          {timestamp && (
            <StatRow
              icon={CalendarClock}
              label="Fecha y hora"
              value={timestamp}
              tooltip={TOOLTIPS.timestamp}
            />
          )}
          <StatRow
            icon={Flame}
            label="Área quemada hasta ahora"
            value={formatNumber(observedAreaHa ?? null, "ha")}
            tooltip={TOOLTIPS.observed}
            emphasized
          />
          <StatRow
            icon={Radar}
            label={
              predictionHorizon === null
                ? "Área total prevista"
                : `Predicción a ${predictionHorizon.toLocaleString("es", { maximumFractionDigits: 1 })} h`
            }
            value={formatNumber(prediction, "ha")}
            tooltip={TOOLTIPS.predicted}
          />
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">No hay estadísticas disponibles para esta ejecución.</div>
      )}
    </div>
  );
}
