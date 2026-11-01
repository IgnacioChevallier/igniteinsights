"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Simulated-time clock for the fire progression animation (VISUALIZACION-ANIMADA.md A1).
 *
 * Driven by `requestAnimationFrame` with **real elapsed deltas**, never a frame counter:
 * a browser that stutters then loses frames, not simulated hours, so the animation keeps
 * meaning the same thing on a loaded laptop as on an idle desktop.
 */

/** 10 real seconds cover the whole horizon, as specified. */
export const DEFAULT_LOOP_SECONDS = 10;

/** Beat at the end before restarting: a hard cut hides where the run actually stops. */
const END_HOLD_MS = 1000;

export const SPEEDS = [0.25, 0.5, 1] as const;
export type Speed = (typeof SPEEDS)[number];

/** Keep the tuned playback rates while presenting the simpler scale requested by users. */
export const SPEED_LABELS: Record<Speed, string> = {
  0.25: "0,5×",
  0.5: "1×",
  1: "1,5×",
};

export type FireClock = {
  /** Current position in simulated hours, in [0, horizonHours]. */
  t: number;
  playing: boolean;
  speed: Speed;
  horizonHours: number;
  /** True when the browser asks for reduced motion; the clock then starts paused at the end. */
  reducedMotion: boolean;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  /** Jump to an hour (the scrubber). Pauses nothing — dragging while playing is allowed. */
  seek: (hours: number) => void;
  setSpeed: (speed: Speed) => void;
};

export function useFireClock({
  horizonHours,
  loopSeconds = DEFAULT_LOOP_SECONDS,
}: {
  horizonHours: number;
  loopSeconds?: number;
}): FireClock {
  const horizon = horizonHours > 0 ? horizonHours : 0;

  // Starts paused on both server and client so hydration cannot mismatch; the mount
  // effect below decides whether to start playing.
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(0.5);
  const [reducedMotion, setReducedMotion] = useState(false);

  const tRef = useRef(0);
  const frameRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const holdUntilRef = useRef(0);

  const write = useCallback((next: number) => {
    tRef.current = next;
    setT(next);
  }, []);

  // A5 · prefers-reduced-motion: start paused showing the final state, which is the
  // frame that carries the information. Anything else animates against the user's setting.
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(query.matches);
    if (query.matches) return;
    setPlaying(true);
  }, []);

  useEffect(() => {
    if (reducedMotion) write(horizon);
  }, [reducedMotion, horizon, write]);

  // Re-clamp when a different run is selected and the horizon shrinks under the cursor.
  useEffect(() => {
    if (tRef.current > horizon) write(horizon);
  }, [horizon, write]);

  useEffect(() => {
    if (!playing || horizon <= 0) return;

    const hoursPerSecond = (horizon / loopSeconds) * speed;

    const tick = (ts: number) => {
      frameRef.current = requestAnimationFrame(tick);

      if (lastTsRef.current === null) {
        lastTsRef.current = ts;
        return;
      }
      const dtSeconds = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;

      // Holding on the final frame before the loop restarts.
      if (holdUntilRef.current) {
        if (ts < holdUntilRef.current) return;
        holdUntilRef.current = 0;
        write(0);
        return;
      }

      const next = tRef.current + dtSeconds * hoursPerSecond;
      if (next >= horizon) {
        write(horizon);
        holdUntilRef.current = ts + END_HOLD_MS;
        return;
      }
      write(next);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
      lastTsRef.current = null;
      holdUntilRef.current = 0;
    };
  }, [playing, horizon, loopSeconds, speed, write]);

  const play = useCallback(() => {
    // Restarting from the end would otherwise sit on the final frame doing nothing.
    if (tRef.current >= horizon) write(0);
    setPlaying(true);
  }, [horizon, write]);

  const pause = useCallback(() => setPlaying(false), []);

  const toggle = useCallback(() => {
    if (playing) pause();
    else play();
  }, [playing, play, pause]);

  const seek = useCallback(
    (hours: number) => {
      holdUntilRef.current = 0;
      write(Math.min(Math.max(hours, 0), horizon));
    },
    [horizon, write],
  );

  return { t, playing, speed, horizonHours: horizon, reducedMotion, play, pause, toggle, seek, setSpeed };
}
