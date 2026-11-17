import { TriangleAlert } from "lucide-react";
import type { EnsembleAgreementContract } from "@/lib/ensemble-agreement";

// Roles frozen before any backtest was scored (DECISIONES-TESIS §6); never reordered by result.
const BAND_ROLE: Record<number, string> = {
  0.8: "alto acuerdo",
  0.5: "escenario central",
  0.1: "propagación posible",
};

export function EnsembleAgreementLegend({ contract }: { contract: EnsembleAgreementContract }) {
  const meta = contract.metadata;

  return (
    <div
      data-testid="ensemble-agreement-legend"
      className="text-xs text-card-foreground"
    >
      <div>
        <ul className="space-y-1.5">
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
