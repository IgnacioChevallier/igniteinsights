"use client";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Opens the one page that owns the ingestion settings.
 *
 * Shared by the "Datos" header and the map sidebar on purpose: both need to reach the
 * same configuration, and a second place to edit sources would be a second place for them
 * to drift. `/settings` writes the single localStorage key `runRealSimulation` reads.
 *
 * A plain anchor, deliberately — not `router.push` and not `next/link`. Both of those
 * navigate inside a React transition, and a transition never commits while the map is
 * open: the progression animation writes clock state on every frame, which starves it
 * indefinitely. Measured from the map, `router.push("/settings")` and a `next/link` click
 * both leave the URL untouched; from the "Datos" section, where nothing animates, the
 * same code navigates. A document navigation cannot be starved, and for a settings page
 * reached now and then the reload costs nothing worth keeping the bug for.
 *
 * The real fix is for the animation to stop driving React state 60 times a second — see
 * `use-fire-clock.ts`. That is a refactor of the animation, not of this button.
 */
export function SettingsButton({
  label,
  variant = "ghost",
  className,
}: {
  /** Icon-only when omitted — the header, where the gear sits among other controls. */
  label?: string;
  variant?: "ghost" | "outline";
  className?: string;
}) {
  return (
    <a
      href="/settings"
      className={cn(buttonVariants({ variant, size: "sm" }), className)}
      aria-label={label ? undefined : "Configuración"}
    >
      <SettingsIcon />
      {label && <span className="ml-1.5">{label}</span>}
    </a>
  );
}

function SettingsIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
