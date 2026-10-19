/** Wire contract emitted by `app.ensemble.agreement` for the future map layer. */

export type EnsembleAgreementThreshold = 0.1 | 0.5 | 0.8;

export type EnsembleAgreementBand = {
  value: EnsembleAgreementThreshold;
  operator: ">=";
  /** Human-readable threshold, formatted for the Spanish UI (for example, `≥ 0,50`). */
  label: string;
  fill_color: string;
  line_color: string;
  geojson: GeoJSON.FeatureCollection<
    GeoJSON.Polygon | GeoJSON.MultiPolygon,
    {
      agreement_threshold: EnsembleAgreementThreshold;
      agreement_label: string;
    }
  >;
};

export type EnsembleAgreementContract = {
  schema_version: 1;
  layer: {
    id: "ensemble_agreement";
    name: "Acuerdo del ensamble";
    /** UI copy is intentional: this metric is agreement, not calibrated probability. */
    legend_label: "acuerdo entre simulaciones";
    /** Consumers must require an explicit user action before drawing or fetching geometry. */
    default_visible: false;
    geometry: "polygon";
  };
  metadata: {
    valid_members: number;
    expected_members: number;
    valid_member_ids: string[];
    failed_members: Record<string, string>;
    weather_cycle: string;
    /** Exact observed-perimeter / simulation start; it need not coincide with the cycle. */
    forecast_start: string;
    horizon_hours: number;
    /** ISO-8601 timestamp for artifact generation. */
    generated_at: string;
    /** ISO-8601 `forecast_start + horizon_hours`, never cycle time plus horizon. */
    forecast_valid_at: string | null;
  };
  /** Ordered low-to-high so a renderer can paint nested polygons in this order. */
  thresholds: EnsembleAgreementBand[];
};

/** Stable sidebar defaults; importing this does not add a source or layer to the map. */
export const ENSEMBLE_AGREEMENT_LAYER = {
  id: "ensemble_agreement",
  name: "Acuerdo del ensamble",
  legendLabel: "acuerdo entre simulaciones",
  defaultVisible: false,
  thresholds: [0.1, 0.5, 0.8] as const,
} as const;

/**
 * Accept only a complete contract: a partial artifact must leave the map as it was, not
 * draw half a legend. Returns the reason in Spanish when the artifact cannot be shown.
 */
export function checkEnsembleAgreement(value: unknown): EnsembleAgreementContract | string {
  const contract = value as Partial<EnsembleAgreementContract> | null;
  const meta = contract?.metadata;
  if (!contract || contract.layer?.id !== "ensemble_agreement" || !meta) {
    return "El artefacto de acuerdo no tiene el formato esperado.";
  }
  if (
    typeof meta.valid_members !== "number" ||
    typeof meta.expected_members !== "number" ||
    meta.expected_members <= 0 ||
    meta.valid_members <= 0 ||
    !meta.weather_cycle ||
    !meta.forecast_start ||
    typeof meta.horizon_hours !== "number" ||
    !meta.forecast_valid_at ||
    !meta.generated_at
  ) {
    return "El artefacto de acuerdo está incompleto: faltan miembros, ciclo, horizonte o vigencia.";
  }
  const values = (contract.thresholds ?? []).map((band) => band?.value);
  const expected = ENSEMBLE_AGREEMENT_LAYER.thresholds;
  if (
    values.length !== expected.length ||
    values.some((v, i) => v !== expected[i]) ||
    contract.thresholds!.some((band) => !Array.isArray(band.geojson?.features))
  ) {
    return "El artefacto de acuerdo está incompleto: faltan bandas ≥ 0,10 / 0,50 / 0,80.";
  }
  return contract as EnsembleAgreementContract;
}

/** One source for the three nested bands, low to high, each feature carrying its colours. */
export function agreementFeatureCollection(
  contract: EnsembleAgreementContract,
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: contract.thresholds.flatMap((band) =>
      band.geojson.features.map((feature) => ({
        ...feature,
        properties: {
          ...feature.properties,
          fill_color: band.fill_color,
          line_color: band.line_color,
        },
      })),
    ),
  };
}
