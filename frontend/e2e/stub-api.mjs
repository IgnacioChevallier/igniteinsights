// Stand-in for the FastAPI backend so the dashboard can be driven by Playwright without
// Python or ELMFIRE. Serves only what the map path touches.
import http from "node:http";

const PORT = Number(process.env.PORT ?? 8000);

const SIM_ID = "11111111-2222-3333-4444-555555555555";
const CENTRE = [-71.8, -42.7];
const HORIZON = 12;

// Ellipses elongated south (wind from the north), growing with time. The API sends
// cumulative burned area as Polygons, polygonised from the time-of-arrival raster — the
// fixture matches that. It used to send raw contour LineStrings, which the map had to
// close itself, and that is what painted lakes as burned.
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
  coords.push(coords[0]); // a Polygon ring has to close
  return coords;
}

function isochrones() {
  const features = [];
  for (let h = 0; h <= HORIZON; h += 1) {
    features.push({
      type: "Feature",
      properties: { arrival_s: h * 3600, arrival_hours: h },
      geometry: { type: "Polygon", coordinates: [ring(h)] },
    });
  }
  // Two untimed features: the converter leaves these null on purpose (A5).
  for (let i = 0; i < 2; i += 1) {
    features.push({
      type: "Feature",
      properties: { arrival_s: null, arrival_hours: null },
      geometry: { type: "Polygon", coordinates: [ring(HORIZON + 1 + i)] },
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

function windField() {
  const width = 8;
  const height = 8;
  const bounds = [-71.9, -42.82, -71.7, -42.58];
  const bands = [];
  for (let hour = 0; hour <= HORIZON; hour += 1) {
    const u = [];
    const v = [];
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        // A gently curving field makes spatial interpolation observable without claiming
        // that this synthetic Playwright fixture is a real forecast.
        u.push(Number((2 + x * 0.55 + hour * 0.08).toFixed(3)));
        v.push(Number((-8 + y * 0.45 + hour * 0.05).toFixed(3)));
      }
    }
    const meanU = 2 + 3.5 * 0.55 + hour * 0.08;
    const meanV = -8 + 3.5 * 0.45 + hour * 0.05;
    const speed = Math.hypot(meanU, meanV);
    const blowsTo = (Math.atan2(meanU, meanV) * 180) / Math.PI + 360;
    bands.push({
      hour,
      u_mph: u,
      v_mph: v,
      speed_min_mph: 4,
      speed_max_mph: 10,
      speed_mph: Number(speed.toFixed(2)),
      blows_to_deg: Number((blowsTo % 360).toFixed(1)),
      direction_consistency: 0.98,
      label: `viento ${speed.toFixed(1).replace(".", ",")} mph hacia el SE`,
    });
  }
  return {
    schema_version: 2,
    bounds,
    ring: [
      [bounds[0], bounds[3]],
      [bounds[2], bounds[3]],
      [bounds[2], bounds[1]],
      [bounds[0], bounds[1]],
      [bounds[0], bounds[3]],
    ],
    width,
    height,
    unit: "mph",
    basis: "elmfire_20ft",
    height_m: 6.096,
    source_model: "GFS 0.25°",
    forecast_start: "2026-09-06T12:00:00Z",
    forecast_cycle: "2026090612",
    step_hours: 1,
    bands,
  };
}

// Three nested bands, low to high, shaped like app.ensemble.agreement's contract.
function ensembleAgreement() {
  const band = (value, label, fill, line, r) => {
    const coords = [];
    for (let i = 0; i <= 32; i += 1) {
      const a = (i / 32) * 2 * Math.PI;
      coords.push([CENTRE[0] + Math.cos(a) * r * 0.75, CENTRE[1] - r * 0.5 + Math.sin(a) * r * 1.3]);
    }
    return {
      value, operator: ">=", label, fill_color: fill, line_color: line,
      geojson: { type: "FeatureCollection", features: [{ type: "Feature", properties: { agreement_threshold: value, agreement_label: label }, geometry: { type: "Polygon", coordinates: [coords] } }] },
    };
  };
  return {
    schema_version: 1,
    layer: { id: "ensemble_agreement", name: "Acuerdo del ensamble", legend_label: "acuerdo entre simulaciones", default_visible: false, geometry: "polygon" },
    metadata: {
      valid_members: 31, expected_members: 31, valid_member_ids: [], failed_members: {},
      weather_cycle: "2026090600", forecast_start: "2026-09-06T12:00:00+00:00", horizon_hours: 12,
      generated_at: "2026-09-06T13:00:00+00:00", forecast_valid_at: "2026-09-07T00:00:00+00:00",
    },
    thresholds: [
      band(0.1, "≥ 0,10", "#fed976", "#b45309", 0.05),
      band(0.5, "≥ 0,50", "#fd8d3c", "#c2410c", 0.038),
      band(0.8, "≥ 0,80", "#bd0026", "#881337", 0.026),
    ],
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

// GET /api/v1/operativo/estado for the client view: one fire whose forecast has the ensemble.
function estado() {
  return {
    modo: "demo",
    ahora: "2026-09-06T15:00:00+00:00",
    latencia_firms_h: 3,
    calcular_ensamble: true,
    ultima_pasada: "2026-09-06T12:00:00+00:00",
    proxima_pasada_estimada: "2026-09-06T19:00:00+00:00",
    horizonte_h: 25,
    incendios: [{
      id: "f-000000000001",
      nombre: "Cerca de Villa Futalaufquen · desde 06-09",
      primera_deteccion: "2026-09-06T12:00:00+00:00",
      ultima_deteccion: "2026-09-06T12:00:00+00:00",
      detecciones: 4,
      bbox: [CENTRE[0] - 0.01, CENTRE[1] - 0.01, CENTRE[0] + 0.01, CENTRE[1] + 0.01],
      pronostico: {
        id: "p-1", simulacion_id: SIM_ID, pasada: "2026-09-06T12:00:00+00:00",
        disponible: "2026-09-06T15:00:00+00:00", ciclo_gfs: "2026-09-06T00:00:00+00:00", ensamble: true,
      },
      actualizacion: { estado: "listo", pasada: "2026-09-06T12:00:00+00:00", error: null },
    }],
    detecciones: { type: "FeatureCollection", features: [] },
  };
}

const ok = (data) => ({ status: "success", data, error: null, meta: { timestamp: new Date().toISOString() } });

http
  .createServer((req, res) => {
    const path = req.url.split("?")[0];
    let body;
    if (path === "/api/v1/dashboard/summary") body = ok(SUMMARY);
    else if (path.endsWith("/isochrones")) body = ok(isochrones());
    else if (path.endsWith("/ignition")) body = ok(ignition());
    else if (path.endsWith("/stats")) body = ok({ rows: [] });
    else if (path.endsWith("/wind")) body = ok(windField());
    else if (path.endsWith("/ensemble-agreement")) body = ok(ensembleAgreement());
    else if (path === "/api/v1/operativo/estado") body = ok(estado());
    else if (path.startsWith("/api/v1/fires/active")) body = ok({ type: "FeatureCollection", features: [] });
    else body = ok(null);
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(body));
  })
  // Configurable so the stub can run alongside a real backend already on :8000.
  .listen(PORT, () => console.log(`stub api on :${PORT}`));
