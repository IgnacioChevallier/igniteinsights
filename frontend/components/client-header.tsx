"use client";

import { BookOpen, CircleUserRound, Map, TriangleAlert } from "lucide-react";
import Image from "next/image";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";
import { useEstado } from "@/lib/operativo";
import { cn } from "@/lib/utils";

const LINKS = [
  { id: "mapa", href: "/", label: "Mapa", icon: Map },
  { id: "documentacion", href: "/documentacion", label: "Documentación", icon: BookOpen },
  { id: "cuenta", href: "/cuenta", label: "Cuenta", icon: CircleUserRound },
] as const;

/**
 * The header of every client page, with the demo banner: a frozen January map must never
 * read as a fire burning today. Plain anchors, not next/link: a transition never commits
 * while the map animation writes state every frame (see settings-button.tsx).
 */
export function ClientHeader({
  active,
  isAdmin = false,
}: {
  active: (typeof LINKS)[number]["id"];
  isAdmin?: boolean;
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
