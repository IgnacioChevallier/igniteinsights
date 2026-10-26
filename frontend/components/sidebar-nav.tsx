"use client";

import {
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

export type DashboardSection = "producto" | "map" | "fuels" | "validation" | "playground" | "data";

const SECTIONS: { id: DashboardSection; label: string; icon: LucideIcon }[] = [
  { id: "producto", label: "Producto", icon: Flame },
  { id: "map", label: "Mapa", icon: Map },
  { id: "fuels", label: "Combustibles", icon: Trees },
  { id: "validation", label: "Validación", icon: Target },
  { id: "playground", label: "Simulador", icon: FlaskConical },
  { id: "data", label: "Datos", icon: Database },
];

export function SidebarNav({
  activeSection,
  onChange,
}: {
  activeSection: DashboardSection;
  onChange: (section: DashboardSection) => void;
}) {
  return (
    <nav className="flex w-56 shrink-0 flex-col gap-1 border-r bg-background p-3">
      <div className="mb-2 flex items-center gap-2 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
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
      {SECTIONS.map((section) => (
        <button
          key={section.id}
          onClick={() => onChange(section.id)}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
            activeSection === section.id
              ? "bg-primary text-primary-foreground"
              : "text-foreground hover:bg-muted",
          )}
        >
          <section.icon className="h-4 w-4 shrink-0" />
          {section.label}
        </button>
      ))}
      {/* Plain anchors, like settings-button.tsx: the map animation starves transitions. */}
      <div className="mt-auto flex flex-col gap-1 border-t pt-3 text-sm">
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- document navigation on purpose, as above */}
        <a href="/?panel=cliente" className="flex items-center gap-2 rounded-md px-3 py-2 hover:bg-muted">
          <Eye className="h-4 w-4 shrink-0" /> Vista cliente
        </a>
        <a href="/documentacion" className="rounded-md px-3 py-1.5 text-muted-foreground hover:bg-muted">
          Documentación
        </a>
        <a href="/cuenta" className="rounded-md px-3 py-1.5 text-muted-foreground hover:bg-muted">
          Cuenta
        </a>
      </div>
    </nav>
  );
}
