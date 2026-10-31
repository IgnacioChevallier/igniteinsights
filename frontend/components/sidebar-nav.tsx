"use client";

import {
  BookOpen,
  CircleUserRound,
  Database,
  Eye,
  FlaskConical,
  Flame,
  Map,
  Target,
  Trees,
  type LucideIcon,
} from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/utils";

export type DashboardSection =
  | "producto"
  | "map"
  | "fuels"
  | "validation"
  | "playground"
  | "data"
  | "documentation";

const SECTIONS: { id: DashboardSection; label: string; icon: LucideIcon }[] = [
  { id: "producto", label: "Producto", icon: Flame },
  { id: "map", label: "Mapa", icon: Map },
  { id: "fuels", label: "Combustibles", icon: Trees },
  { id: "validation", label: "Validación", icon: Target },
  { id: "playground", label: "Simulador", icon: FlaskConical },
  { id: "data", label: "Datos", icon: Database },
  { id: "documentation", label: "Documentación", icon: BookOpen },
];

export function SidebarNav({
  activeSection,
  onChange,
}: {
  activeSection: DashboardSection;
  onChange: (section: DashboardSection) => void;
}) {
  return (
    <nav
      aria-label="Secciones principales"
      className="w-full shrink-0 border-b bg-background md:flex md:w-56 md:flex-col md:gap-1 md:border-b-0 md:border-r md:p-3"
    >
      <div className="flex h-12 items-center gap-2 border-b px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground md:mb-2 md:h-auto md:border-b-0 md:px-2">
        <Image
          src="/images/igniteinsights-celdas.svg"
          alt=""
          aria-hidden="true"
          width={20}
          height={20}
          className="h-5 w-5 shrink-0"
        />
        <span>Ignite Insights</span>
      </div>
      <div className="flex overflow-x-auto p-2 md:flex-col md:gap-1 md:overflow-visible md:p-0">
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            type="button"
            onClick={() => onChange(section.id)}
            aria-current={activeSection === section.id ? "page" : undefined}
            className={cn(
              "flex min-w-[5.25rem] shrink-0 flex-col items-center gap-1 rounded-md px-2 py-2 text-center text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:min-w-0 md:flex-row md:gap-2 md:px-3 md:text-left md:text-sm",
              activeSection === section.id
                ? "bg-primary text-primary-foreground"
                : "text-foreground hover:bg-muted",
            )}
          >
            <section.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            {section.label}
          </button>
        ))}
      </div>
      {/* Plain anchors, like settings-button.tsx: the map animation starves transitions. */}
      <div className="flex gap-1 border-t p-2 text-sm md:mt-auto md:flex-col md:pt-3">
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- document navigation on purpose, as above */}
        <a href="/?panel=cliente" className="flex items-center gap-2 rounded-md px-3 py-2 hover:bg-muted">
          <Eye className="h-4 w-4 shrink-0" aria-hidden="true" /> Vista cliente
        </a>
        <a
          href="/cuenta"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-muted-foreground hover:bg-muted"
        >
          <CircleUserRound className="h-4 w-4 shrink-0" aria-hidden="true" /> Cuenta
        </a>
      </div>
    </nav>
  );
}
