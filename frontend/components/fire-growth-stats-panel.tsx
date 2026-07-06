import { Clock, Flame, type LucideIcon } from "lucide-react";
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
  horizon:
    "Tiempo total simulado por ELMFIRE, en horas desde la ignición. Puede diferir levemente del horizonte solicitado por redondeos internos del intervalo de tiempo.",
  totalArea:
    "Área total acumulada quemada desde la ignición hasta el final del horizonte simulado — es el crecimiento completo del incendio, no una medición puntual.",
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

export function FireGrowthStatsPanel({ row }: { row: FireSizeStatsRow | null }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Resumen de crecimiento
      </div>
      {row ? (
        <div className="flex flex-col gap-3">
          <StatRow
            icon={Flame}
            label="Área total quemada"
            value={formatNumber(
              row.total_fire_area_ac !== null ? row.total_fire_area_ac * AC_TO_HA : null,
              "ha",
            )}
            tooltip={TOOLTIPS.totalArea}
            emphasized
          />
          <StatRow
            icon={Clock}
            label="Horizonte"
            value={formatNumber(row.tstop_h, "h")}
            tooltip={TOOLTIPS.horizon}
          />
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">No hay estadísticas disponibles para esta ejecución.</div>
      )}
    </div>
  );
}
