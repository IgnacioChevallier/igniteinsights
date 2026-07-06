"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  type IngestionSettings,
} from "@/components/dashboard-header";

type SourceConfig = {
  key: keyof Pick<
    IngestionSettings,
    "include_firms" | "include_dem" | "include_gfs" | "include_worldcover" | "include_canopy"
  >;
  label: string;
  description: string;
  note?: string;
};

const SOURCES: SourceConfig[] = [
  {
    key: "include_firms",
    label: "FIRMS — Detecciones de incendios",
    description: "Detecciones de fuego activo NASA VIIRS NOAA-20 NRT. Se actualiza cada ~12 horas.",
  },
  {
    key: "include_gfs",
    label: "GFS — Pronóstico meteorológico",
    description: "NOAA GFS 0.25° de viento, temperatura y humedad. Se actualiza cada 6 horas.",
  },
  {
    key: "include_dem",
    label: "DEM — Elevación del terreno",
    description: "Modelo digital de elevación Copernicus GLO-30 (30 m).",
    note: "Estático: descargar una vez.",
  },
  {
    key: "include_worldcover",
    label: "WorldCover — Cobertura del suelo",
    description: "Clasificación de cobertura del suelo ESA WorldCover 10 m.",
    note: "Estático: descargar una vez.",
  },
  {
    key: "include_canopy",
    label: "Canopy — Cobertura y altura del bosque",
    description: "Hansen GFC treecover2000 (cc) + ETH Global Canopy Height 2020 (ch).",
    note: "Estático: descargar una vez. ~500 MB.",
  },
];

export default function SettingsPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<IngestionSettings>(DEFAULT_SETTINGS);
  const [mounted, setMounted] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
    setMounted(true);
  }, []);

  function update<K extends keyof IngestionSettings>(key: K, value: IngestionSettings[K]) {
    const next = { ...settings, [key]: value };
    setSettings(next);
    if (!mounted) return;

    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      saveSettings(next);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    }, 300);
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-6 py-8">
        <div className="mb-6 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            ← Volver
          </Button>
          <div className="flex-1" />
          {saved && <span className="text-xs text-muted-foreground">Guardado</span>}
        </div>

        <h1 className="text-2xl font-semibold">Configuración</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura qué fuentes se incluyen cuando haces clic en{" "}
          <span className="font-medium text-foreground">Ejecutar</span> en el panel. La configuración
          se guarda automáticamente en tu navegador.
        </p>

        <Separator className="my-6" />

        {/* ── Fuentes de ingesta ─────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Fuentes de ingesta</CardTitle>
            <CardDescription>
              Activa qué fuentes de datos se descargan en cada ejecución.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 divide-y">
            {SOURCES.map(({ key, label, description, note }) => (
              <div key={key} className="flex items-start justify-between gap-4 py-4 first:pt-0 last:pb-0">
                <div className="space-y-0.5">
                  <label htmlFor={key} className="cursor-pointer text-sm font-medium leading-none">
                    {label}
                    {note && (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        {note}
                      </span>
                    )}
                  </label>
                  <p className="text-xs text-muted-foreground">{description}</p>
                </div>
                <Switch
                  id={key}
                  checked={settings[key] as boolean}
                  onCheckedChange={(v) => update(key, v)}
                />
              </div>
            ))}
          </CardContent>
        </Card>

        <Separator className="my-6" />

        {/* ── Configuración de FIRMS ─────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Configuración de FIRMS</CardTitle>
            <CardDescription>
              Se aplica cuando FIRMS está activado. Deja la fecha de inicio vacía para usar los datos más recientes.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-1.5">
              <label htmlFor="firms_start_date" className="text-sm font-medium">
                Fecha de inicio
              </label>
              <input
                id="firms_start_date"
                type="date"
                value={settings.firms_start_date}
                onChange={(e) => update("firms_start_date", e.target.value)}
                className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <p className="text-xs text-muted-foreground">
                Déjala vacía para solicitar los datos disponibles más recientes de FIRMS.
              </p>
            </div>

            <div className="grid gap-1.5">
              <label htmlFor="firms_day_range" className="text-sm font-medium">
                Rango de días
                <span className="ml-1 font-normal text-muted-foreground">(1 – 5)</span>
              </label>
              <input
                id="firms_day_range"
                type="number"
                min={1}
                max={5}
                value={settings.firms_day_range}
                onChange={(e) =>
                  update("firms_day_range", Math.max(1, Math.min(5, Number(e.target.value))))
                }
                className="h-9 w-28 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <p className="text-xs text-muted-foreground">
                Cantidad de días a solicitar a FIRMS (máximo 5).
              </p>
            </div>
          </CardContent>
        </Card>

        <Separator className="my-6" />

        <div className="flex justify-end">
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            ← Volver al panel
          </Button>
        </div>
      </div>
    </main>
  );
}
