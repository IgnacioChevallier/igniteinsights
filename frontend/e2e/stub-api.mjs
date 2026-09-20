// Stand-in for the FastAPI backend so the dashboard can be driven by Playwright without
// Python or ELMFIRE. Serves only what the map path touches.
import http from "node:http";

const PORT = Number(process.env.PORT ?? 8000);

const SIM_ID = "11111111-2222-3333-4444-555555555555";
const CENTRE = [-71.8, -42.7];
const HORIZON = 12;

// Ellipses elongated south (wind from the north), growing with time. gdal_contour runs
// without -p, so the real isochrones are LineStrings — the fixture matches that.
function ring(hours) {
  const grow = 0.004 + hours * 0.0035;
  const coords = [];
  for (let i = 0; i <= 64; i += 1) {
    const a = (i / 64) * 2 * Math.PI;
    // Push the centre south as it grows, and stretch it along that axis.
    const south = -grow * 0.55;
    coords.push([
      CENTRE[0] + Math.cos(a) * grow * 0.75,
      CENTRE[1] + south + Math.sin(a) * grow * 1.35,
    ]);
  }
  return coords;
}

function isochrones() {
  const features = [];
  for (let h = 0; h <= HORIZON; h += 1) {
    features.push({
      type: "Feature",
      properties: { arrival_s: h * 3600, arrival_hours: h },
      geometry: { type: "LineString", coordinates: ring(h) },
    });
  }
  // Two untimed contours: the converter leaves these null on purpose (A5).
  for (let i = 0; i < 2; i += 1) {
    features.push({
      type: "Feature",
      properties: { arrival_s: null, arrival_hours: null },
      geometry: { type: "LineString", coordinates: ring(HORIZON + 1 + i) },
    });
  }
  return { type: "FeatureCollection", features };
}

function ignition() {
  const r = 0.0035;
  const coords = [];
  for (let i = 0; i <= 32; i += 1) {
    const a = (i / 32) * 2 * Math.PI;
    coords.push([CENTRE[0] + Math.cos(a) * r * 0.9, CENTRE[1] + Math.sin(a) * r]);
  }
  return {
    type: "FeatureCollection",
    features: [{ type: "Feature", properties: { source: "FIRMS" }, geometry: { type: "Polygon", coordinates: [coords] } }],
  };
}

const RUN = {
  id: SIM_ID,
  kind: "simulation",
  source: "elmfire",
  aoi: "los-alerces",
  status: "success",
  horizon_hours: HORIZON,
  ignition_datetime: "2026-09-06T12:00:00Z",
  started_at: "2026-09-06T12:00:00Z",
  finished_at: "2026-09-06T12:05:00Z",
  error_message: null,
  warnings: null,
};

const SUMMARY = {
  generated_at: new Date().toISOString(),
  expected_elmfire_inputs: [],
  summary: {
    latest_ingestion_status: "success",
    latest_simulation_status: "success",
    raster_asset_count: 0,
    ready_input_folder_count: 1,
    input_folder_count: 1,
    output_folder_count: 1,
  },
  runs: [RUN],
  raster_assets: [],
  simulation_outputs: [],
  elmfire_inputs: [],
  elmfire_outputs: [],
};

const ok = (data) => ({ status: "success", data, error: null, meta: { timestamp: new Date().toISOString() } });

http
  .createServer((req, res) => {
    const path = req.url.split("?")[0];
    let body;
    if (path === "/api/v1/dashboard/summary") body = ok(SUMMARY);
    else if (path.endsWith("/isochrones")) body = ok(isochrones());
    else if (path.endsWith("/ignition")) body = ok(ignition());
    else if (path.endsWith("/stats")) body = ok({ rows: [] });
    else if (path.startsWith("/api/v1/fires/active")) body = ok({ type: "FeatureCollection", features: [] });
    else body = ok(null);
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(body));
  })
  // Configurable so the stub can run alongside a real backend already on :8000.
  .listen(PORT, () => console.log(`stub api on :${PORT}`));
