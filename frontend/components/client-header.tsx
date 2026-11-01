"use client";

import { BookOpen, ChevronDown, CircleUserRound, Flame, Map, TriangleAlert } from "lucide-react";
import Image from "next/image";
import { useEffect, useRef } from "react";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";
import { useEstado, type Incendio } from "@/lib/operativo";
import { cn } from "@/lib/utils";

const LINKS = [
  { id: "mapa", href: "/", label: "Mapa", icon: Map },
  { id: "documentacion", href: "/documentacion", label: "Documentación", icon: BookOpen },
  { id: "cuenta", href: "/cuenta", label: "Cuenta", icon: CircleUserRound },
] as const;

/**
 * Fire picker: native <details> so there is no popover dependency; closes on pick and on
 * any click outside. Label collapses to the icon on phones, where the nav already fills the row.
 */
function IncendioSelector({
  incendios,
  elegido,
  onElegir,
}: {
  incendios: Incendio[];
  elegido: string | null;
  onElegir: (id: string) => void;
}) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) ref.current.open = false;
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);
  const actual = incendios.find((i) => i.id === elegido) ?? incendios[0];
  return (
    <details ref={ref} className="relative ml-auto">
      <summary
        aria-label="Incendios activos"
        className="flex cursor-pointer list-none items-center gap-1.5 rounded-md border px-2 py-1.5 text-xs font-medium hover:bg-muted sm:text-sm [&::-webkit-details-marker]:hidden"
      >
        <Flame className="h-4 w-4 shrink-0 text-orange-600" aria-hidden="true" />
        <span className="hidden max-w-64 truncate sm:inline">{actual.nombre.split(" · ")[0]}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      </summary>
      <ul className="absolute right-0 top-full z-50 mt-1 w-80 max-w-[calc(100vw-1.5rem)] rounded-md border bg-background p-1 shadow-lg">
        <li className="px-2 py-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Incendios activos
        </li>
        {incendios.map((i) => (
          <li key={i.id}>
            <button
              type="button"
              onClick={() => {
                onElegir(i.id);
                if (ref.current) ref.current.open = false;
              }}
              aria-current={i.id === actual.id ? "true" : undefined}
              className={cn(
                "w-full rounded px-2 py-1.5 text-left text-sm hover:bg-muted",
                i.id === actual.id && "bg-primary/5 font-medium",
              )}
            >
              {i.nombre.split(" · ")[0]}
              <span className="block text-xs font-normal text-muted-foreground">
                {formatArgentinaDateTime(i.primera_deteccion)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}

/**
 * The header of every client page, with the demo banner: a frozen January map must never
 * read as a fire burning today. Plain anchors, not next/link: a transition never commits
 * while the map animation writes state every frame (see settings-button.tsx).
 */
export function ClientHeader({
  active,
  isAdmin = false,
  elegido = null,
  onElegir,
}: {
  active: (typeof LINKS)[number]["id"];
  isAdmin?: boolean;
  /** Map page only: shows the fire picker when given `onElegir`. */
  elegido?: string | null;
  onElegir?: (id: string) => void;
}) {
  const { estado } = useEstado(300_000);

  return (
    <header className="shrink-0 border-b bg-background">
      <div className="flex items-center justify-between gap-2 px-3 py-2 sm:justify-start sm:gap-6 sm:px-4">
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- document navigation on purpose: transitions never commit while the map animates */}
        <a href="/" className="flex items-center gap-2">
          <Image
            src="/images/igniteinsights-celdas.svg"
            alt=""
            aria-hidden="true"
            width={28}
            height={28}
            className="h-7 w-7"
          />
          <span className="hidden text-base font-semibold tracking-tight min-[430px]:inline">
            IgniteInsights
          </span>
        </a>
        <nav className="flex min-w-0 items-center gap-0.5 text-xs sm:gap-1 sm:text-sm">
          {LINKS.map((link) => (
            <a
              key={link.id}
              href={link.href}
              aria-current={active === link.id ? "page" : undefined}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2 py-1.5 font-medium transition-colors sm:px-3",
                active === link.id ? "bg-primary text-primary-foreground" : "hover:bg-muted",
              )}
            >
              <link.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {link.label}
            </a>
          ))}
          {isAdmin && (
            // eslint-disable-next-line @next/next/no-html-link-for-pages -- same reason as above
            <a href="/?panel=admin" className="hidden rounded-md px-3 py-1.5 text-muted-foreground hover:bg-muted sm:block">
              Panel admin
            </a>
          )}
        </nav>
        {onElegir && estado && estado.incendios.length > 0 && (
          <IncendioSelector incendios={estado.incendios} elegido={elegido} onElegir={onElegir} />
        )}
      </div>
      {active === "mapa" && estado?.modo === "demo" && (
        <div
          role="status"
          className="flex items-start gap-2 border-t border-amber-500/40 bg-amber-500/15 px-3 py-1.5 text-[11px] leading-snug text-foreground sm:items-center sm:px-4 sm:text-xs"
        >
          <TriangleAlert className="h-3.5 w-3.5 shrink-0 text-amber-600" />
          <span>
            <strong>Modo demostración.</strong> El panel muestra lo que se habría visto el{" "}
            {formatArgentinaDateTime(estado.ahora)} {ARGENTINA_TIME_ZONE_LABEL}. No es un incendio
            en curso.
          </span>
        </div>
      )}
    </header>
  );
}
