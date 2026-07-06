// Mirrors the YlOrRd 5-stop ramp used server-side in app/postprocessing/raster_overlay.py.
const RAMP_CSS =
  "linear-gradient(to right, rgb(255,255,178), rgb(254,204,92), rgb(253,141,60), rgb(240,59,32), rgb(189,0,38))";

export function RasterLegend({
  label,
  valueRange,
  unit,
}: {
  label: string;
  valueRange: [number, number];
  unit: string;
}) {
  const [min, max] = valueRange;
  return (
    <div className="rounded-md border bg-card px-3 py-2 text-xs text-card-foreground shadow-md">
      <div className="mb-1 font-medium">{label}</div>
      <div className="h-2 w-40 rounded-full" style={{ backgroundImage: RAMP_CSS }} />
      <div className="mt-1 flex w-40 justify-between text-muted-foreground">
        <span>
          {min.toLocaleString(undefined, { maximumFractionDigits: 1 })} {unit}
        </span>
        <span>
          {max.toLocaleString(undefined, { maximumFractionDigits: 1 })} {unit}
        </span>
      </div>
    </div>
  );
}
