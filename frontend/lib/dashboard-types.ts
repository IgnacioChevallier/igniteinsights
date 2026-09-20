export type Run = {
  id: string;
  kind: "ingestion" | "simulation";
  source: string;
  category?: string;
  aoi: string;
  status: string;
  horizon_hours?: number;
  ignition_datetime?: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  warnings?: string[] | null;
  metadata?: Record<string, unknown> | null;
};

export type RasterAsset = {
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

export type FileInfo = {
  name: string;
  path: string;
  size_bytes: number;
  modified_at: string;
};

export type InputFolder = {
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

export type OutputFolder = {
  name: string;
  path: string;
  modified_at: string;
  file_count: number;
  files: FileInfo[];
};

export type SimulationOutput = {
  id: string;
  simulation_id: string;
  output_type: string;
  file_path: string | null;
  valid_at: string | null;
  created_at: string | null;
  simulation_status: string;
};

export type DashboardData = {
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
