import { TriangleAlert } from "lucide-react";
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
  return (
    <div
      data-testid="ensemble-agreement-legend"
      className="rounded-md border bg-card px-3 py-2 text-xs text-card-foreground shadow-md"
    >
      <div className="mb-1 font-medium">{contract.layer.legend_label}</div>
      <ul className="space-y-0.5">
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
      {meta.valid_members < meta.expected_members && (
        <p className="mt-2 flex items-start gap-1 text-[11px] text-amber-700 dark:text-amber-400">
          <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
          Ensamble incompleto: el acuerdo se calcula sobre {meta.valid_members} miembros válidos.
        </p>
      )}
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[10px] leading-snug text-muted-foreground">
        <dt>Miembros válidos</dt>
        <dd className="tabular-nums text-foreground">
          {meta.valid_members}/{meta.expected_members}
        </dd>
        <dt>Ciclo meteorológico</dt>
        <dd className="text-foreground">{formatCycle(meta.weather_cycle)}</dd>
        <dt>Inicio del pronóstico</dt>
        <dd className="text-foreground">{at(meta.forecast_start)}</dd>
        <dt>Horizonte</dt>
        <dd className="text-foreground">{meta.horizon_hours} h</dd>
        <dt>Vigencia</dt>
        <dd className="text-foreground">hasta {at(meta.forecast_valid_at!)}</dd>
        <dt>Generado</dt>
        <dd className="text-foreground">{at(meta.generated_at)}</dd>
      </dl>
      <p className="mt-2 text-[10px] leading-snug text-muted-foreground">
        Fracción de simulaciones meteorológicas que alcanzan cada zona.{" "}
        <strong className="font-medium text-foreground">No es una probabilidad calibrada.</strong>{" "}
        Muestra propagación potencial y no considera combate ni supresión. Sólo varía la
        meteorología: el incendio real puede extenderse fuera de la zona ≥ 0,10.
      </p>
    </div>
  );
}
