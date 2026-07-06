"use client";

import { Database, Map, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type DashboardSection = "map" | "data";

const SECTIONS: { id: DashboardSection; label: string; icon: LucideIcon }[] = [
  { id: "map", label: "Mapa", icon: Map },
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
      <div className="mb-2 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Ignite Insights
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
    </nav>
  );
}
