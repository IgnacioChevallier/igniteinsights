"use client";

import { useState } from "react";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { DashboardHeader } from "@/components/dashboard-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MapPanel } from "@/components/map-panel";
import { SidebarNav, type DashboardSection } from "@/components/sidebar-nav";
import type {
  DashboardData,
  Run,
  RasterAsset,
  InputFolder,
  OutputFolder,
  SimulationOutput,
} from "@/lib/dashboard-types";

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("es", {
    timeZone: "UTC",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDecimal(value: number) {
  return value.toLocaleString("es", { maximumFractionDigits: 1 });
}

function formatBytes(value: number | null) {
  if (value === null) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${formatDecimal(value / 1024)} KB`;
  if (value < 1024 * 1024 * 1024) return `${formatDecimal(value / 1024 / 1024)} MB`;
  return `${formatDecimal(value / 1024 / 1024 / 1024)} GB`;
}

function shortId(id: string) {
  return id.length > 12 ? `${id.slice(0, 8)}...` : id;
}

function statusVariant(status: string): BadgeProps["variant"] {
  const normalized = status.toLowerCase();
  if (["success", "completed", "ready"].includes(normalized)) return "success";
  if (["failed", "error"].includes(normalized)) return "destructive";
  if (["running", "pending", "partial_failure", "skipped"].includes(normalized)) {
    return "warning";
  }
  if (normalized === "none") return "muted";
  return "secondary";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: "Completado",
    error: "Error",
    failed: "Fallido",
    incomplete: "Incompleto",
    none: "Sin datos",
    partial_failure: "Falla parcial",
    pending: "Pendiente",
    ready: "Listo",
    running: "En ejecución",
    skipped: "Omitido",
    success: "Éxito",
  };
  return labels[status.toLowerCase()] ?? status;
}

function runKindLabel(kind: Run["kind"]) {
  return kind === "ingestion" ? "Ingesta" : "Simulación";
}

function dataTypeLabel(value: string) {
  const labels: Record<string, string> = {
    fireline_intensity: "Intensidad del frente de fuego",
    isochrones: "Isócronas",
    time_of_arrival: "Tiempo de llegada",
  };
  return labels[value] ?? value;
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
      {label}
    </div>
  );
}

function SummaryCard({
  title,
  value,
  detail,
  status,
}: {
  title: string;
  value: string;
  detail: string;
  status?: string;
}) {
  return (
    <Card>
      <CardHeader className="p-4 pb-2">
        <CardDescription className="text-xs">{title}</CardDescription>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-2xl font-semibold">{value}</div>
            <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
          </div>
          {status ? <Badge variant={statusVariant(status)}>{statusLabel(status)}</Badge> : null}
        </div>
      </CardContent>
    </Card>
  );
}

function RunsTable({ runs }: { runs: Run[] }) {
  if (!runs.length) return <EmptyState label="No se encontraron ejecuciones previas." />;

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ejecución</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Fuente</TableHead>
              <TableHead>AOI</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Inicio</TableHead>
              <TableHead>Fin</TableHead>
              <TableHead>Descripción</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={`${run.kind}-${run.id}`}>
                <TableCell className="font-mono text-xs">{shortId(run.id)}</TableCell>
                <TableCell>{runKindLabel(run.kind)}</TableCell>
                <TableCell>{run.source}</TableCell>
                <TableCell>{run.aoi}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(run.status)}>{statusLabel(run.status)}</Badge>
                </TableCell>
                <TableCell>{formatDate(run.started_at)}</TableCell>
                <TableCell>{formatDate(run.finished_at)}</TableCell>
                <TableCell className="max-w-64 truncate text-muted-foreground">
                  {run.metadata?.skipped
                    ? "Datos ya presentes"
                    : run.error_message ?? "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function InputsTable({ folders }: { folders: InputFolder[] }) {
  if (!folders.length) return <EmptyState label="No se encontraron carpetas de entrada ELMFIRE." />;

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Carpeta</TableHead>
              <TableHead>Preparación</TableHead>
              <TableHead>Archivos</TableHead>
              <TableHead>Faltantes</TableHead>
              <TableHead>Modificado</TableHead>
              <TableHead>Ruta</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {folders.map((folder) => (
              <TableRow key={folder.path}>
                <TableCell className="font-mono text-xs">{folder.name}</TableCell>
                <TableCell>
                  <Badge variant={folder.ready ? "success" : "warning"}>
                    {folder.ready ? "Listo" : "Incompleto"}
                  </Badge>
                </TableCell>
                <TableCell>
                  {folder.present_count}/{folder.expected_count}
                </TableCell>
                <TableCell className="max-w-96">
                  {folder.missing_files.length ? (
                    <ScrollArea className="h-12">
                      <div className="flex flex-wrap gap-1 pr-3">
                        {folder.missing_files.map((file) => (
                          <Badge key={file} variant="outline">
                            {file}
                          </Badge>
                        ))}
                      </div>
                    </ScrollArea>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell>{formatDate(folder.modified_at)}</TableCell>
                <TableCell className="max-w-80 truncate font-mono text-xs text-muted-foreground">
                  {folder.path}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function AssetsTable({ assets }: { assets: RasterAsset[] }) {
  if (!assets.length) return <EmptyState label="No hay activos ráster registrados." />;

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tipo</TableHead>
              <TableHead>Fuente</TableHead>
              <TableHead>Existe</TableHead>
              <TableHead>CRS</TableHead>
              <TableHead>Resolución</TableHead>
              <TableHead>Tamaño</TableHead>
              <TableHead>Creado</TableHead>
              <TableHead>Ruta</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {assets.map((asset) => (
              <TableRow key={asset.id}>
                <TableCell className="font-medium">{dataTypeLabel(asset.asset_type)}</TableCell>
                <TableCell>{asset.source ?? "-"}</TableCell>
                <TableCell>
                  <Badge variant={asset.file_exists ? "success" : "destructive"}>
                    {asset.file_exists ? "Sí" : "No"}
                  </Badge>
                </TableCell>
                <TableCell>{asset.crs ?? "-"}</TableCell>
                <TableCell>{asset.resolution_m ? `${asset.resolution_m} m` : "-"}</TableCell>
                <TableCell>{formatBytes(asset.file_size_bytes)}</TableCell>
                <TableCell>{formatDate(asset.created_at)}</TableCell>
                <TableCell className="max-w-80 truncate font-mono text-xs text-muted-foreground">
                  {asset.file_path}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function OutputsTable({
  folders,
  registeredOutputs,
}: {
  folders: OutputFolder[];
  registeredOutputs: SimulationOutput[];
}) {
  if (!folders.length && !registeredOutputs.length) {
    return <EmptyState label="No se encontraron salidas ELMFIRE." />;
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Carpetas de salida</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Carpeta</TableHead>
                <TableHead>Archivos</TableHead>
                <TableHead>Modificado</TableHead>
                <TableHead>Ruta</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {folders.map((folder) => (
                <TableRow key={folder.path}>
                  <TableCell className="font-mono text-xs">{folder.name}</TableCell>
                  <TableCell>{folder.file_count}</TableCell>
                  <TableCell>{formatDate(folder.modified_at)}</TableCell>
                  <TableCell className="max-w-96 truncate font-mono text-xs text-muted-foreground">
                    {folder.path}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Salidas registradas</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {registeredOutputs.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Simulación</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Creado</TableHead>
                  <TableHead>Ruta</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {registeredOutputs.map((output) => (
                  <TableRow key={output.id}>
                    <TableCell>{dataTypeLabel(output.output_type)}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {shortId(output.simulation_id)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(output.simulation_status)}>
                        {statusLabel(output.simulation_status)}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDate(output.created_at)}</TableCell>
                    <TableCell className="max-w-96 truncate font-mono text-xs text-muted-foreground">
                      {output.file_path ?? "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-5 text-sm text-muted-foreground">No hay salidas registradas.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function DashboardShell({
  data,
  apiBaseUrl,
}: {
  data: DashboardData;
  apiBaseUrl: string;
}) {
  const [activeSection, setActiveSection] = useState<DashboardSection>("map");

  return (
    <div className="flex h-screen">
      <SidebarNav activeSection={activeSection} onChange={setActiveSection} />

      <div className="flex flex-1 flex-col overflow-hidden">
        {activeSection === "data" && (
          <div className="shrink-0 px-6 py-6">
            <DashboardHeader generatedAt={formatDate(data.generated_at)} apiBaseUrl={apiBaseUrl} />
          </div>
        )}

        {activeSection === "data" && (
          <div className="flex-1 overflow-auto px-6 pb-6">
            <Separator className="mb-6" />

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <SummaryCard
                title="Última ingesta"
                value={statusLabel(data.summary.latest_ingestion_status)}
                detail={`${data.runs.filter((run) => run.kind === "ingestion").length} ejecuciones recientes`}
                status={data.summary.latest_ingestion_status}
              />
              <SummaryCard
                title="Última simulación"
                value={statusLabel(data.summary.latest_simulation_status)}
                detail={`${data.runs.filter((run) => run.kind === "simulation").length} ejecuciones recientes`}
                status={data.summary.latest_simulation_status}
              />
              <SummaryCard
                title="Activos ráster"
                value={`${data.summary.raster_asset_count}`}
                detail="registrados en PostGIS"
              />
              <SummaryCard
                title="Preparación de entradas"
                value={`${data.summary.ready_input_folder_count}/${data.summary.input_folder_count}`}
                detail="carpetas ELMFIRE completas"
                status={
                  data.summary.ready_input_folder_count > 0
                    ? "ready"
                    : data.summary.input_folder_count > 0
                      ? "pending"
                      : "none"
                }
              />
            </section>

            <Tabs defaultValue="runs" className="mt-6">
              <TabsList>
                <TabsTrigger value="runs">Ejecuciones</TabsTrigger>
                <TabsTrigger value="inputs">Entradas</TabsTrigger>
                <TabsTrigger value="assets">Activos</TabsTrigger>
                <TabsTrigger value="outputs">Salidas</TabsTrigger>
              </TabsList>
              <TabsContent value="runs">
                <RunsTable runs={data.runs} />
              </TabsContent>
              <TabsContent value="inputs">
                <InputsTable folders={data.elmfire_inputs} />
              </TabsContent>
              <TabsContent value="assets">
                <AssetsTable assets={data.raster_assets} />
              </TabsContent>
              <TabsContent value="outputs">
                <OutputsTable
                  folders={data.elmfire_outputs}
                  registeredOutputs={data.simulation_outputs}
                />
              </TabsContent>
            </Tabs>
          </div>
        )}

        {activeSection === "map" && (
          <div className="min-h-0 flex-1">
            <MapPanel runs={data.runs} />
          </div>
        )}
      </div>
    </div>
  );
}
