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
    label: "FIRMS — Fire detections",
    description: "NASA VIIRS NOAA-20 NRT active fire detections. Updated ~every 12 hours.",
  },
  {
    key: "include_gfs",
    label: "GFS — Weather forecast",
    description: "NOAA GFS 0.25° wind, temperature, and humidity. Updated every 6 hours.",
  },
  {
    key: "include_dem",
    label: "DEM — Terrain elevation",
    description: "Copernicus GLO-30 digital elevation model (30 m).",
    note: "Static — download once.",
  },
  {
    key: "include_worldcover",
    label: "WorldCover — Land cover",
    description: "ESA WorldCover 10 m land cover classification.",
    note: "Static — download once.",
  },
  {
    key: "include_canopy",
    label: "Canopy — Forest cover & height",
    description: "Hansen GFC treecover2000 (cc) + ETH Global Canopy Height 2020 (ch).",
    note: "Static — download once. ~500 MB.",
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
            ← Back
          </Button>
          <div className="flex-1" />
          {saved && <span className="text-xs text-muted-foreground">Saved</span>}
        </div>

        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure which sources are included when you click{" "}
          <span className="font-medium text-foreground">Run</span> on the dashboard. Settings are
          saved automatically to your browser.
        </p>

        <Separator className="my-6" />

        {/* ── Ingestion sources ─────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Ingestion sources</CardTitle>
            <CardDescription>
              Toggle which data sources are downloaded on each run.
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

        {/* ── FIRMS settings ────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>FIRMS settings</CardTitle>
            <CardDescription>
              Applied when FIRMS is enabled. Leave start date empty to use the most recent data.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-1.5">
              <label htmlFor="firms_start_date" className="text-sm font-medium">
                Start date
              </label>
              <input
                id="firms_start_date"
                type="date"
                value={settings.firms_start_date}
                onChange={(e) => update("firms_start_date", e.target.value)}
                className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <p className="text-xs text-muted-foreground">
                Leave empty to request the most recent available data from FIRMS.
              </p>
            </div>

            <div className="grid gap-1.5">
              <label htmlFor="firms_day_range" className="text-sm font-medium">
                Day range
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
                Number of days to request from FIRMS (max 5).
              </p>
            </div>
          </CardContent>
        </Card>

        <Separator className="my-6" />

        <div className="flex justify-end">
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            ← Back to dashboard
          </Button>
        </div>
      </div>
    </main>
  );
}
