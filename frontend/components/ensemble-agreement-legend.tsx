import { Info, TriangleAlert } from "lucide-react";
import { Tooltip } from "@/components/ui/tooltip";
import type { EnsembleAgreementContract } from "@/lib/ensemble-agreement";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";

// Roles frozen before any backtest was scored (DECISIONES-TESIS §6); never reordered by result.
const BAND_ROLE: Record<number, string> = {
  0.8: "alto acuerdo",
  0.5: "escenario central",
  0.1: "propagación posible",
};

/** "2023020512" → "2023-02-05 12 UTC"; anything else is shown as received. */
function formatCycle(cycle: string): string {
  const m = /^(\d{4})(\d{2})(\d{2})(\d{2})$/.exec(cycle);
  return m ? `GEFS ${m[1]}-${m[2]}-${m[3]} ${m[4]} UTC` : cycle;
}

export function EnsembleAgreementLegend({ contract }: { contract: EnsembleAgreementContract }) {
  const meta = contract.metadata;
  const at = (iso: string) => `${formatArgentinaDateTime(iso)} ${ARGENTINA_TIME_ZONE_LABEL}`;
  const metadata = [
    `Miembros válidos: ${meta.valid_members}/${meta.expected_members}`,
    `Ciclo meteorológico: ${formatCycle(meta.weather_cycle)}`,
    `Inicio del pronóstico: ${at(meta.forecast_start)}`,
    `Horizonte: ${meta.horizon_hours} h`,
    `Vigencia: hasta ${at(meta.forecast_valid_at!)}`,
    `Generado: ${at(meta.generated_at)}`,
  ].join("\n");

  return (
    <div
      data-testid="ensemble-agreement-legend"
      className="text-xs text-card-foreground"
    >
      <div className="flex items-start justify-between gap-3">
        <ul className="min-w-0 flex-1 space-y-1.5">
          {[...contract.thresholds].reverse().map((band) => (
            <li key={band.value} className="flex items-center gap-2">
              <span
                className="h-3 w-3 shrink-0 rounded-sm border"
                style={{ backgroundColor: band.fill_color, borderColor: band.line_color }}
              />
              <span className="tabular-nums">{band.label}</span>
              <span className="text-muted-foreground">{BAND_ROLE[band.value]}</span>
            </li>
          ))}
        </ul>
        <Tooltip content={<span className="whitespace-pre-line leading-relaxed">{metadata}</span>}>
          <button
            type="button"
            aria-label="Información del acuerdo del ensamble"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <Info className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </Tooltip>
      </div>
      {meta.valid_members < meta.expected_members && (
        <p className="mt-2 flex items-start gap-1 text-[11px] text-amber-700 dark:text-amber-400">
          <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
          Ensamble incompleto: el acuerdo se calcula sobre {meta.valid_members} miembros válidos.
        </p>
      )}
    </div>
  );
}
