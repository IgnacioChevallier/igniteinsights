"use client";

import { SPEEDS, type FireClock, type Speed } from "@/hooks/use-fire-clock";
import { formatSimulatedHour, realTimestamp } from "@/lib/isochrone-clock";
import { ARGENTINA_TIME_ZONE_LABEL } from "@/lib/date-time";
import { cn } from "@/lib/utils";

export type IsochroneHorizonControl = {
  valueHours: number;
  maxHours: number;
  onChange: (hours: number) => void;
};

/**
 * Play/pause, scrubber and speed for the fire progression animation
 * (docs/historico/VISUALIZACION-ANIMADA.md A3).
 *
 * The scrubber is not optional garnish: the loop cannot be the only mode, because
 * reading a specific hour is the whole point of having the times per feature.
 */
export function FireAnimationControls({
  clock,
  ignitionDatetime = null,
  untimedCount = 0,
  horizonControl,
  className,
}: {
  clock: FireClock;
  ignitionDatetime?: string | null;
  /** Features the converter left without `arrival_s`; excluded from the animation. */
  untimedCount?: number;
  /** Optional cap for how many forecast hours the map exposes. */
  horizonControl?: IsochroneHorizonControl;
  className?: string;
}) {
  const { t, playing, speed, horizonHours, reducedMotion } = clock;
  // Both readouts come off the same rounded value, or the label says "2,0 h" while the
  // timestamp says 13:58 and the two appear to disagree.
  const shown = Math.round(t * 10) / 10;
  const stamp = realTimestamp(ignitionDatetime, shown);

  return (
    <div
      className={cn(
        "rounded-md border bg-card/95 px-3 py-2 text-xs shadow-md backdrop-blur",
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={clock.toggle}
          aria-label={playing ? "Pausar animación" : "Reproducir animación"}
          aria-pressed={playing}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-sm hover:bg-accent"
        >
          {playing ? "❚❚" : "▶"}
        </button>

        <input
          type="range"
          min={0}
          max={horizonHours}
          step="any"
          value={t}
          onChange={(e) => clock.seek(Number(e.target.value))}
          aria-label="Hora simulada"
          className="h-1 min-w-0 flex-1 cursor-pointer accent-orange-500"
        />

        <div className="shrink-0 text-right leading-tight">
          <div className="font-mono font-medium tabular-nums">{formatSimulatedHour(shown)}</div>
          <div className="text-[10px] text-muted-foreground">
            de {formatSimulatedHour(horizonHours)}
          </div>
        </div>

        <div className="flex shrink-0 overflow-hidden rounded-md border">
          {SPEEDS.map((s: Speed) => (
            <button
              key={s}
              type="button"
              onClick={() => clock.setSpeed(s)}
              aria-pressed={speed === s}
              className={cn(
                "px-1.5 py-0.5 text-[10px] tabular-nums",
                speed === s ? "bg-primary text-primary-foreground" : "bg-background hover:bg-accent",
              )}
            >
              {s.toLocaleString("es")}×
            </button>
          ))}
        </div>
      </div>

      {horizonControl && (
        <div className="mt-2 flex items-center gap-3 border-t pt-2">
          <span className="shrink-0 font-medium">Isócronas hasta</span>
          <input
            type="range"
            min={Math.min(1, horizonControl.maxHours)}
            max={horizonControl.maxHours}
            step={1}
            value={horizonControl.valueHours}
            onChange={(e) => horizonControl.onChange(Number(e.target.value))}
            aria-label="Horizonte visible de isócronas"
            className="h-1 min-w-20 flex-1 cursor-pointer accent-orange-500"
          />
          <output className="w-9 shrink-0 text-right font-mono font-semibold tabular-nums">
            {horizonControl.valueHours.toLocaleString("es", { maximumFractionDigits: 1 })} h
          </output>
        </div>
      )}

      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-muted-foreground">
        {stamp && <span>Hora real estimada: {stamp} {ARGENTINA_TIME_ZONE_LABEL}</span>}
        {reducedMotion && <span>Movimiento reducido: inicia en pausa sobre el estado final.</span>}
        {untimedCount > 0 && (
          <span className="text-amber-700 dark:text-amber-400">
            {untimedCount} {untimedCount === 1 ? "isócrona sin" : "isócronas sin"} tiempo de
            llegada, excluida{untimedCount === 1 ? "" : "s"} de la animación.
          </span>
        )}
      </div>
    </div>
  );
}
