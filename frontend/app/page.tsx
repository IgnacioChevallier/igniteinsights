import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

type DashboardEnvelope = {
  status: string;
  data: DashboardData;
  error: { message?: string } | null;
  meta: { timestamp: string };
};

type Run = {
  id: string;
  kind: "ingestion" | "simulation";
  source: string;
  category?: string;
  aoi: string;
  status: string;
  horizon_hours?: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
};

type RasterAsset = {
  id: string;
  asset_type: string;
  file_path: string;
  crs: string | null;
  resolution_m: number | null;
  band_count: number | null;
  dtype: string | null;
  file_size_bytes: number | null;
  created_at: string | null;
  source: string | null;
  aoi: string | null;
  file_exists: boolean;
};

type FileInfo = {
  name: string;
  path: string;
  size_bytes: number;
  modified_at: string;
};

type InputFolder = {
  name: string;
  path: string;
  modified_at: string;
  present_count: number;
  expected_count: number;
  missing_count: number;
  present_files: string[];
  missing_files: string[];
  files: FileInfo[];
  ready: boolean;
};

type OutputFolder = {
  name: string;
  path: string;
  modified_at: string;
  file_count: number;
  files: FileInfo[];
};

type SimulationOutput = {
  id: string;
  simulation_id: string;
  output_type: string;
  file_path: string | null;
  valid_at: string | null;
  created_at: string | null;
  simulation_status: string;
};

type DashboardData = {
  generated_at: string;
  expected_elmfire_inputs: string[];
  summary: {
    latest_ingestion_status: string;
    latest_simulation_status: string;
    raster_asset_count: number;
    ready_input_folder_count: number;
    input_folder_count: number;
    output_folder_count: number;
  };
  runs: Run[];
  raster_assets: RasterAsset[];
  simulation_outputs: SimulationOutput[];
  elmfire_inputs: InputFolder[];
  elmfire_outputs: OutputFolder[];
};

async function getDashboardData() {
  const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/dashboard/summary`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        apiBaseUrl,
        data: null,
        error: `API returned ${response.status}`,
      };
    }

    const envelope = (await response.json()) as DashboardEnvelope;
    return { apiBaseUrl, data: envelope.data, error: null };
  } catch (error) {
    return {
      apiBaseUrl,
      data: null,
      error: error instanceof Error ? error.message : "Unable to reach API",
    };
  }
}

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatBytes(value: number | null) {
  if (value === null) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
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
          {status ? <Badge variant={statusVariant(status)}>{status}</Badge> : null}
        </div>
      </CardContent>
    </Card>
  );
}

function RunsTable({ runs }: { runs: Run[] }) {
  if (!runs.length) return <EmptyState label="No previous runs found." />;

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Run</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>AOI</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Finished</TableHead>
              <TableHead>Error</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={`${run.kind}-${run.id}`}>
                <TableCell className="font-mono text-xs">{shortId(run.id)}</TableCell>
                <TableCell className="capitalize">{run.kind}</TableCell>
                <TableCell>{run.source}</TableCell>
                <TableCell>{run.aoi}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                </TableCell>
                <TableCell>{formatDate(run.started_at)}</TableCell>
                <TableCell>{formatDate(run.finished_at)}</TableCell>
                <TableCell className="max-w-64 truncate text-muted-foreground">
                  {run.error_message ?? "-"}
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
  if (!folders.length) return <EmptyState label="No ELMFIRE input folders found." />;

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Folder</TableHead>
              <TableHead>Readiness</TableHead>
              <TableHead>Files</TableHead>
              <TableHead>Missing</TableHead>
              <TableHead>Modified</TableHead>
              <TableHead>Path</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {folders.map((folder) => (
              <TableRow key={folder.path}>
                <TableCell className="font-mono text-xs">{folder.name}</TableCell>
                <TableCell>
                  <Badge variant={folder.ready ? "success" : "warning"}>
                    {folder.ready ? "ready" : "incomplete"}
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
  if (!assets.length) return <EmptyState label="No raster assets registered." />;

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Exists</TableHead>
              <TableHead>CRS</TableHead>
              <TableHead>Resolution</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Path</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {assets.map((asset) => (
              <TableRow key={asset.id}>
                <TableCell className="font-medium">{asset.asset_type}</TableCell>
                <TableCell>{asset.source ?? "-"}</TableCell>
                <TableCell>
                  <Badge variant={asset.file_exists ? "success" : "destructive"}>
                    {asset.file_exists ? "yes" : "no"}
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
    return <EmptyState label="No ELMFIRE outputs found." />;
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Output folders</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Folder</TableHead>
                <TableHead>Files</TableHead>
                <TableHead>Modified</TableHead>
                <TableHead>Path</TableHead>
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
          <CardTitle>Registered outputs</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {registeredOutputs.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Simulation</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Path</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {registeredOutputs.map((output) => (
                  <TableRow key={output.id}>
                    <TableCell>{output.output_type}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {shortId(output.simulation_id)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(output.simulation_status)}>
                        {output.simulation_status}
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
            <div className="p-5 text-sm text-muted-foreground">No registered outputs.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default async function DashboardPage() {
  const { apiBaseUrl, data, error } = await getDashboardData();

  if (error || !data) {
    return (
      <main className="mx-auto flex min-h-screen max-w-6xl items-center justify-center p-6">
        <Card className="w-full max-w-xl">
          <CardHeader>
            <CardTitle>ELMFIRE Dashboard</CardTitle>
            <CardDescription>API unavailable at {apiBaseUrl}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Badge variant="destructive">{error ?? "Unknown error"}</Badge>
            <form>
              <Button type="submit" variant="outline" size="sm">
                Refresh
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-6 py-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">ELMFIRE Dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Generated {formatDate(data.generated_at)} from {apiBaseUrl}
            </p>
          </div>
          <form>
            <Button type="submit" variant="outline" size="sm">
              Refresh
            </Button>
          </form>
        </header>

        <Separator className="my-6" />

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            title="Latest ingestion"
            value={data.summary.latest_ingestion_status}
            detail={`${data.runs.filter((run) => run.kind === "ingestion").length} recent runs`}
            status={data.summary.latest_ingestion_status}
          />
          <SummaryCard
            title="Latest simulation"
            value={data.summary.latest_simulation_status}
            detail={`${data.runs.filter((run) => run.kind === "simulation").length} recent runs`}
            status={data.summary.latest_simulation_status}
          />
          <SummaryCard
            title="Raster assets"
            value={`${data.summary.raster_asset_count}`}
            detail="registered in PostGIS"
          />
          <SummaryCard
            title="Input readiness"
            value={`${data.summary.ready_input_folder_count}/${data.summary.input_folder_count}`}
            detail="complete ELMFIRE folders"
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
            <TabsTrigger value="runs">Runs</TabsTrigger>
            <TabsTrigger value="inputs">Inputs</TabsTrigger>
            <TabsTrigger value="assets">Assets</TabsTrigger>
            <TabsTrigger value="outputs">Outputs</TabsTrigger>
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
    </main>
  );
}
