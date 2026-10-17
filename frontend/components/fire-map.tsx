"use client";

import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import maplibregl, { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { FUEL_PATTERN_IDS, fuelPatternImage } from "@/lib/fuel-pattern";
import {
  compassPoint,
  sampleWindField,
  startWindParticles,
  type WindField,
  type WindParticleController,
} from "@/lib/wind-particles";

// Los Alerces National Park, Patagonia — matches the AOI these simulations run over.
const INITIAL_CENTER: [number, number] = [-71.8, -42.7];
const INITIAL_ZOOM = 10;

const FIRES_SOURCE_ID = "active-fires";
const ISOCHRONES_SOURCE_ID = "isochrones";
const IGNITION_SOURCE_ID = "ignition-perimeter";
const TOA_SOURCE_ID = "time-of-arrival-overlay";
const FLIN_SOURCE_ID = "fireline-intensity-overlay";
const FUELS_SOURCE_ID = "fuels-overlay";
const SYNTHETIC_SOURCE_ID = "synthetic-scenario";
const WIND_SURFACE_SOURCE_ID = "wind-speed-surface";
const WIND_SURFACE_LAYER_ID = `${WIND_SURFACE_SOURCE_ID}-layer`;

// Two tokenless basemaps, both loaded up front and toggled via layout.visibility
// (not map.setStyle(), which would wipe every custom source/layer below).
const STREET_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const SATELLITE_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
// Tokenless elevation for the optional 3D view. Fetched only while terrain is on: a source
// no layer uses loads no tiles, so the 2D map never touches it.
const TERRAIN_TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";
const TERRAIN_EXAGGERATION = 1.5;

const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    street: { type: "raster", tiles: [STREET_TILES], tileSize: 256, attribution: "© OpenStreetMap contributors" },
    satellite: {
      type: "raster",
      tiles: [SATELLITE_TILES],
      tileSize: 256,
      attribution: "Teselas © Esri - Fuente: Esri, Maxar, Earthstar Geographics",
    },
    terrain: {
      type: "raster-dem",
      tiles: [TERRAIN_TILES],
      encoding: "terrarium",
      tileSize: 256,
      maxzoom: 15,
      attribution: "Relieve: Mapzen Terrain Tiles (SRTM y otras fuentes)",
    },
  },
  layers: [
    // First, so everything else draws on top. A synthetic scenario assumes flat ground and
    // one fuel class; a satellite image under it shows terrain the scenario denies.
    {
      id: "synthetic",
      type: "background",
      paint: { "background-color": "#eceae4" },
      layout: { visibility: "none" },
    },
    { id: "street", type: "raster", source: "street", layout: { visibility: "none" } },
    { id: "satellite", type: "raster", source: "satellite" },
  ],
};

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

// Shared with the terrain thumbnails in the playground sidebar, so the picture you click
// and the map you get are the same blue.
export const WATER_COLOR = "#4b83c4";

/** The wind field's own grey, shared with the legends that explain it. */
export const WIND_COLOR = "#475569";

export type Basemap = "street" | "satellite" | "synthetic";

// ── Fire progression animation (docs/historico/VISUALIZACION-ANIMADA.md parte 1) ──────────────────────
//
// Three layers over the same isochrone source, filtered on `arrival_hours` against the
// clock. A feature the converter could not time carries `arrival_hours = null`; every
// filter below reads it through `coalesce(..., UNTIMED)` and requires `>= 0`, so those
// features are excluded from all three layers rather than being drawn at a made-up time.
const UNTIMED = -1;
const ARRIVAL: maplibregl.ExpressionSpecification = ["coalesce", ["get", "arrival_hours"], UNTIMED];
const IS_TIMED: maplibregl.ExpressionSpecification = [">=", ARRIVAL, 0];

const BURNED_LAYER = `${ISOCHRONES_SOURCE_ID}-line`;
const BURNED_FILL_LAYER = `${ISOCHRONES_SOURCE_ID}-burned-fill`;
const FRONT_LAYER = `${ISOCHRONES_SOURCE_ID}-front`;
const PENDING_LAYER = `${ISOCHRONES_SOURCE_ID}-pending`;

export type FireClockView = {
  /** Position in simulated hours. */
  t: number;
  /** One isochrone step (DTDUMP in hours) — the width of the active front band. */
  stepHours: number;
  horizonHours: number;
};

/** Temporal colour ramp over the run's own horizon, so the burned interior keeps its
 *  time reading instead of flattening into one colour. */
function arrivalRamp(horizonHours: number): maplibregl.ExpressionSpecification {
  const end = horizonHours > 0 ? horizonHours : 12;
  return [
    "interpolate",
    ["linear"],
    ARRIVAL,
    UNTIMED, "#999999",
    0, "#fee08b",
    end / 2, "#fc8d59",
    end, "#b30000",
  ];
}

export type ImageOverlay = {
  image_base64: string;
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
};

export type RasterOverlayData = ImageOverlay & {
  value_range: [number, number];
  unit: string;
};

export function FireMap({
  activeFires = null,
  isochrones = null,
  ignitionPerimeter = null,
  timeOfArrivalOverlay = null,
  firelineIntensityOverlay = null,
  fuelsOverlay = null,
  fitTo = null,
  clock = null,
  overlay = null,
  syntheticLayers = null,
  windField = null,
  windTimeHours = 0,
  windSurfaceVisible = false,
  initialBasemap = "satellite",
}: {
  activeFires?: GeoJSON.FeatureCollection | null;
  isochrones?: GeoJSON.FeatureCollection | null;
  ignitionPerimeter?: GeoJSON.FeatureCollection | null;
  timeOfArrivalOverlay?: RasterOverlayData | null;
  firelineIntensityOverlay?: RasterOverlayData | null;
  fuelsOverlay?: ImageOverlay | null;
  /** Zoom to this collection when it changes. The initial view frames the whole AOI,
   *  which leaves a 12 km synthetic playground domain as a speck. */
  fitTo?: GeoJSON.FeatureCollection | null;
  /** Drives the progression animation. `null` draws every isochrone at once, which is
   *  the pre-animation behaviour and what a caller that has no clock should get. */
  clock?: FireClockView | null;
  /** Rendered inside the map container, above the legend — the animation controls. */
  overlay?: React.ReactNode;
  /** What a synthetic scenario *is*: a uniform slab of one fuel model, the ignition disc
   *  and the forcing vectors. Built server-side by playground.builder so the geometry and
   *  the colour can never disagree with the run that produced them. */
  syntheticLayers?: GeoJSON.FeatureCollection | null;
  /** Uniform wind to animate over `ring`. The playground derives it from its scenario; the
   *  map reads the run's own ws/wd rasters. Memoise it — a fresh object each render
   *  restarts the animation. */
  windField?: WindField | null;
  /** Fractional simulated time. Unlike the snapped fire view, wind blends continuously. */
  windTimeHours?: number;
  /** Optional low-opacity speed wash underneath the fire result. */
  windSurfaceVisible?: boolean;
  initialBasemap?: Basemap;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  // State, not a ref: every effect below has to re-run once the style finishes loading.
  // As a ref it silently dropped whatever had already arrived — data that resolved before
  // the `load` event left its source empty for the lifetime of the map, because the load
  // handler could only see the props captured when the map was created (all null).
  const [loaded, setLoaded] = useState(false);
  const [basemap, setBasemap] = useState<Basemap>(initialBasemap);
  // Off whenever the basemap is synthetic: that scenario assumes flat ground, and draping
  // it over real relief would deny it. The 3D button is disabled there.
  const [terrain3d, setTerrain3d] = useState(false);
  const windCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const windControllerRef = useRef<WindParticleController | null>(null);
  const windTimeRef = useRef(windTimeHours);
  windTimeRef.current = windTimeHours;
  const [windHover, setWindHover] = useState<{
    x: number;
    y: number;
    speedMph: number;
    azimuthDeg: number;
  } | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      // The synthetic scenario, added before everything else so it sits at the bottom.
      // Vegetation textures, registered before the layer that names them: a fill-pattern
      // pointing at a missing image draws nothing at all, silently.
      for (const id of FUEL_PATTERN_IDS) {
        const image = fuelPatternImage(id, Math.min(window.devicePixelRatio || 1, 2));
        if (image && !map.hasImage(id)) {
          map.addImage(id, image, { pixelRatio: Math.min(window.devicePixelRatio || 1, 2) });
        }
      }

      map.addSource(SYNTHETIC_SOURCE_ID, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: `${SYNTHETIC_SOURCE_ID}-domain`,
        type: "fill",
        source: SYNTHETIC_SOURCE_ID,
        filter: ["==", ["get", "kind"], "domain"],
        // Muted on purpose: the slab is context, the isochrones are the result. At 0.75
        // the pale early contours were unreadable against it.
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.45 },
      });
      map.addLayer({
        id: `${SYNTHETIC_SOURCE_ID}-domain-outline`,
        type: "line",
        source: SYNTHETIC_SOURCE_ID,
        filter: ["==", ["get", "kind"], "domain"],
        paint: { "line-color": "#57534e", "line-width": 1 },
      });
      // Over the slab, under the vectors and the ignition: the lake is part of the
      // ground, not an annotation on top of it.
      map.addLayer({
        id: `${SYNTHETIC_SOURCE_ID}-water`,
        type: "fill",
        source: SYNTHETIC_SOURCE_ID,
        filter: ["==", ["get", "kind"], "water"],
        // Opaque, unlike the 0.45 slab: an unburnable patch has to read as a hole in the
        // fuel, not as more fuel in a different shade.
        paint: { "fill-color": WATER_COLOR, "fill-opacity": 1 },
      });
      // Added after the lake, not before: the lake's fill is opaque and was painting
      // over the wave texture. Ink over colour, in two layers on purpose: fill-pattern cannot be tinted, so
      // baking the colour into the tile would fork the fuel palette between this file and
      // fuels_builder. This way the server still owns every colour.
      map.addLayer({
        id: `${SYNTHETIC_SOURCE_ID}-domain-texture`,
        type: "fill",
        source: SYNTHETIC_SOURCE_ID,
        filter: ["in", ["get", "kind"], ["literal", ["domain", "water"]]],
        paint: { "fill-pattern": ["get", "pattern"], "fill-opacity": 0.85 },
      });
      map.addLayer({
        id: `${SYNTHETIC_SOURCE_ID}-vectors`,
        type: "line",
        source: SYNTHETIC_SOURCE_ID,
        // Slope only. Wind stopped being an arrow: it is animated as drifting particles
        // on the canvas above, the way Windy draws a flow field.
        filter: ["==", ["get", "kind"], "slope"],
        paint: { "line-color": "#57534e", "line-width": 2.5 },
      });
      map.addLayer({
        id: `${SYNTHETIC_SOURCE_ID}-ignition`,
        type: "fill",
        source: SYNTHETIC_SOURCE_ID,
        filter: ["==", ["get", "kind"], "ignition"],
        paint: { "fill-color": "#b30000", "fill-opacity": 0.9 },
      });

      // Observed FIRMS perimeter the run started from. Added first so it sits UNDER
      // the isochrones: it is input, not prediction, and is typically the large
      // majority of the burned area a run reports. Muted grey-blue hatch-free fill
      // deliberately shares no colour with the YlOrRd prediction ramp.
      map.addSource(IGNITION_SOURCE_ID, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: `${IGNITION_SOURCE_ID}-fill`,
        type: "fill",
        source: IGNITION_SOURCE_ID,
        paint: { "fill-color": "#5b6b7a", "fill-opacity": 0.35 },
      });
      map.addSource(ISOCHRONES_SOURCE_ID, { type: "geojson", data: EMPTY_FC });

      // Pending — what the run will still burn. A faint dashed shadow of the final
      // result rather than nothing, so the animation reads as filling in a known
      // outcome instead of growing into a void.
      map.addLayer({
        id: PENDING_LAYER,
        type: "line",
        source: ISOCHRONES_SOURCE_ID,
        paint: { "line-color": "#cbd5e1", "line-width": 0.8, "line-opacity": 0.25 },
      });

      // Burned — accumulated area. The server sends real Polygons, polygonised off the
      // time-of-arrival raster: unburned ground inside the front (a lake) arrives as a
      // hole and is never filled. Filling the raw contour LineStrings, as this did
      // before, made MapLibre close every open contour with a chord straight across the
      // water. Kept low so the stacked bands read as depth.
      map.addLayer({
        id: BURNED_FILL_LAYER,
        type: "fill",
        source: ISOCHRONES_SOURCE_ID,
        paint: { "fill-color": arrivalRamp(12), "fill-opacity": 0.18 },
      });

      map.addLayer({
        id: BURNED_LAYER,
        type: "line",
        source: ISOCHRONES_SOURCE_ID,
        paint: { "line-color": arrivalRamp(12), "line-width": 2, "line-opacity": 0.65 },
      });

      // Active front — where the fire is advancing *now*. Bright and wide against the
      // dark end of the burned ramp; this contrast is what gives the sense of movement.
      map.addLayer({
        id: FRONT_LAYER,
        type: "line",
        source: ISOCHRONES_SOURCE_ID,
        paint: {
          "line-color": "#fff4c2",
          "line-width": 4,
          "line-blur": 1.5,
          "line-opacity": 0.95,
        },
      });

      // A4 · the observed seed's outline goes on TOP of everything predicted. Below the
      // isochrone fill it is swallowed within an hour of simulated time, and the map then
      // shows no boundary between what FIRMS observed and what the model actually spread.
      map.addLayer({
        id: `${IGNITION_SOURCE_ID}-outline`,
        type: "line",
        source: IGNITION_SOURCE_ID,
        paint: {
          "line-color": "#e2e8f0",
          "line-width": 2,
          "line-dasharray": [3, 2],
          "line-opacity": 0.9,
        },
      });

      map.addSource(FIRES_SOURCE_ID, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: `${FIRES_SOURCE_ID}-circle`,
        type: "circle",
        source: FIRES_SOURCE_ID,
        paint: {
          "circle-radius": 5,
          "circle-color": "#e11d48",
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 1,
        },
      });

      for (const layerId of [BURNED_LAYER, FRONT_LAYER, `${FIRES_SOURCE_ID}-circle`]) {
        map.on("click", layerId, (e) => {
          const feature = e.features?.[0];
          if (!feature) return;
          new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(
              `<pre style="margin:0;font-size:11px;">${JSON.stringify(
                feature.properties,
                null,
                2,
              )}</pre>`,
            )
            .addTo(map);
        });
        map.on("mouseenter", layerId, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layerId, () => {
          map.getCanvas().style.cursor = "";
        });
      }

      setLoaded(true);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      setLoaded(false);
    };
  }, []);

  useEffect(() => {
    if (!loaded || !mapRef.current) return;
    const source = mapRef.current.getSource(FIRES_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    source?.setData(activeFires ?? EMPTY_FC);
  }, [activeFires, loaded]);

  useEffect(() => {
    if (!loaded || !mapRef.current) return;
    const source = mapRef.current.getSource(ISOCHRONES_SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined;
    source?.setData(isochrones ?? EMPTY_FC);
  }, [isochrones, loaded]);

  useEffect(() => {
    if (!loaded || !mapRef.current) return;
    const source = mapRef.current.getSource(IGNITION_SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined;
    source?.setData(ignitionPerimeter ?? EMPTY_FC);
  }, [ignitionPerimeter, loaded]);

  // A2 · the animation itself: one filter update per clock tick, no data round-trip.
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;

    if (!clock) {
      // No clock: every timed isochrone at once, nothing highlighted, nothing pending.
      map.setFilter(BURNED_LAYER, IS_TIMED);
      map.setFilter(BURNED_FILL_LAYER, IS_TIMED);
      map.setFilter(FRONT_LAYER, ["==", ["literal", 1], 0]);
      map.setFilter(PENDING_LAYER, ["==", ["literal", 1], 0]);
      return;
    }

    const { t, stepHours } = clock;
    const burned: maplibregl.FilterSpecification = ["all", IS_TIMED, ["<=", ARRIVAL, t]];

    map.setFilter(BURNED_LAYER, burned);
    map.setFilter(BURNED_FILL_LAYER, burned);
    map.setFilter(FRONT_LAYER, [
      "all",
      IS_TIMED,
      [">", ARRIVAL, t - stepHours],
      ["<=", ARRIVAL, t],
    ]);
    map.setFilter(PENDING_LAYER, ["all", IS_TIMED, [">", ARRIVAL, t]]);
  }, [clock, loaded]);

  // The ramp spans the run's horizon, so it is rebuilt when the run changes — not on
  // every clock tick, which would repaint 60 times a second for nothing.
  //
  // Without a clock this used to fall back to 12 h, which stretched the colour ramp over
  // twice the length of a 6 h run — the front never reached the red end — and printed
  // "0 → 12 h" in the legend for a run that stopped at 6. The isochrones carry the answer:
  // the last arrival time IS the horizon.
  const isochroneHorizon = useMemo(() => {
    let max = 0;
    for (const feature of isochrones?.features ?? []) {
      const hours = Number(feature.properties?.arrival_hours);
      if (Number.isFinite(hours)) max = Math.max(max, hours);
    }
    return max;
  }, [isochrones]);
  const horizonHours = clock?.horizonHours ?? isochroneHorizon;
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    const ramp = arrivalRamp(horizonHours);
    map.setPaintProperty(BURNED_LAYER, "line-color", ramp);
    map.setPaintProperty(BURNED_FILL_LAYER, "fill-color", ramp);
  }, [horizonHours, loaded]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map || !fitTo?.features?.length) return;
    const bounds = new maplibregl.LngLatBounds();
    let any = false;
    const walk = (coords: unknown): void => {
      if (Array.isArray(coords) && typeof coords[0] === "number") {
        bounds.extend(coords as [number, number]);
        any = true;
        return;
      }
      if (Array.isArray(coords)) coords.forEach(walk);
    };
    for (const feature of fitTo.features) {
      if (feature.geometry && "coordinates" in feature.geometry) {
        walk((feature.geometry as { coordinates: unknown }).coordinates);
      }
    }
    if (any) map.fitBounds(bounds, { padding: 40, duration: 600, maxZoom: 14 });
  }, [fitTo, loaded]);

  useEffect(() => {
    if (!loaded || !mapRef.current) return;
    const source = mapRef.current.getSource(SYNTHETIC_SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined;
    source?.setData(syntheticLayers ?? EMPTY_FC);
  }, [syntheticLayers, loaded]);

  // One controller per field, not per clock tick: fractional time updates the vectors in
  // place so the trails do not blink away at every forecast hour.
  useEffect(() => {
    const map = mapRef.current;
    const canvas = windCanvasRef.current;
    if (
      !loaded ||
      !map ||
      !canvas ||
      !windField ||
      (windField.kind === "uniform" && windField.speedMph < 0.5)
    ) return;

    const surfaceCanvas = document.createElement("canvas");
    const [west, south, east, north] = windFieldBounds(windField);
    map.addSource(WIND_SURFACE_SOURCE_ID, {
      type: "canvas",
      canvas: surfaceCanvas,
      animate: true,
      coordinates: [
        [west, north],
        [east, north],
        [east, south],
        [west, south],
      ],
    });
    map.addLayer(
      {
        id: WIND_SURFACE_LAYER_ID,
        type: "raster",
        source: WIND_SURFACE_SOURCE_ID,
        paint: {
          "raster-opacity": windSurfaceVisible ? 0.25 : 0,
          "raster-fade-duration": 0,
          "raster-resampling": "linear",
        },
      },
      map.getLayer(`${IGNITION_SOURCE_ID}-fill`) ? `${IGNITION_SOURCE_ID}-fill` : undefined,
    );

    const controller = startWindParticles(map, canvas, windField, {
      timeHours: windTimeRef.current,
      surfaceCanvas,
      surfaceVisible: windSurfaceVisible,
      showParticles: !terrain3d,
    });
    windControllerRef.current = controller;
    return () => {
      controller.stop();
      windControllerRef.current = null;
      setWindHover(null);
      if (mapRef.current === map) {
        if (map.getLayer(WIND_SURFACE_LAYER_ID)) map.removeLayer(WIND_SURFACE_LAYER_ID);
        if (map.getSource(WIND_SURFACE_SOURCE_ID)) map.removeSource(WIND_SURFACE_SOURCE_ID);
      }
    };
    // Visibility and time update the live controller in the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [windField, loaded, terrain3d]);

  useEffect(() => {
    windControllerRef.current?.setTime(windTimeHours);
  }, [windTimeHours]);

  useEffect(() => {
    const map = mapRef.current;
    windControllerRef.current?.setSurfaceVisible(windSurfaceVisible);
    if (loaded && map?.getLayer(WIND_SURFACE_LAYER_ID)) {
      map.setPaintProperty(WIND_SURFACE_LAYER_ID, "raster-opacity", windSurfaceVisible ? 0.25 : 0);
    }
  }, [windSurfaceVisible, loaded]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map || !windField) {
      setWindHover(null);
      return;
    }
    const onMove = (event: maplibregl.MapMouseEvent) => {
      const sample = sampleWindField(
        windField,
        event.lngLat.lng,
        event.lngLat.lat,
        windTimeRef.current,
      );
      if (!sample || sample.speedMph < 0.5) {
        setWindHover(null);
        return;
      }
      setWindHover({
        x: Math.min(event.point.x + 12, map.getContainer().clientWidth - 180),
        y: Math.min(event.point.y + 12, map.getContainer().clientHeight - 54),
        speedMph: sample.speedMph,
        azimuthDeg: sample.azimuthDeg,
      });
    };
    const onLeave = () => setWindHover(null);
    map.on("mousemove", onMove);
    map.on("mouseout", onLeave);
    return () => {
      map.off("mousemove", onMove);
      map.off("mouseout", onLeave);
    };
  }, [windField, loaded]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    for (const id of ["street", "satellite", "synthetic"] as const) {
      map.setLayoutProperty(id, "visibility", basemap === id ? "visible" : "none");
    }
  }, [basemap, loaded]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;
    if (terrain3d) {
      map.setTerrain({ source: "terrain", exaggeration: TERRAIN_EXAGGERATION });
      map.easeTo({ pitch: 60 });
    } else if (map.getTerrain()) {
      map.setTerrain(null);
      map.easeTo({ pitch: 0, bearing: 0 });
    }
  }, [terrain3d, loaded]);

  useImageOverlay(mapRef, loaded, TOA_SOURCE_ID, timeOfArrivalOverlay);
  useImageOverlay(mapRef, loaded, FLIN_SOURCE_ID, firelineIntensityOverlay);
  useImageOverlay(mapRef, loaded, FUELS_SOURCE_ID, fuelsOverlay);

  return (
    <div className="relative h-full w-full" data-terrain={terrain3d ? "on" : "off"}>
      <div ref={containerRef} className="h-full w-full" />
      {/* Above the map, below every control. Nothing here is interactive. */}
      <canvas
        ref={windCanvasRef}
        data-testid="wind-particle-canvas"
        data-wind-surface-visible={windSurfaceVisible ? "true" : "false"}
        className="pointer-events-none absolute inset-0 z-[1]"
      />
      {windHover && (
        <div
          data-testid="wind-hover-readout"
          className="pointer-events-none absolute z-10 rounded-md border border-white/25 bg-slate-950/85 px-2 py-1 text-[10px] font-medium tracking-wide text-white shadow-lg backdrop-blur-sm"
          style={{ left: windHover.x, top: windHover.y }}
        >
          {windHover.speedMph.toLocaleString("es", { maximumFractionDigits: 1 })} mph · hacia el{" "}
          {compassPoint(windHover.azimuthDeg)}
        </div>
      )}
      <div className="absolute left-2 top-2 z-10 overflow-hidden rounded-md border bg-card text-xs shadow-md">
        <button
          className={`px-2 py-1 ${basemap === "street" ? "bg-primary text-primary-foreground" : ""}`}
          onClick={() => setBasemap("street")}
        >
          Calles
        </button>
        <button
          className={`px-2 py-1 ${basemap === "satellite" ? "bg-primary text-primary-foreground" : ""}`}
          onClick={() => setBasemap("satellite")}
        >
          Satélite
        </button>
        {syntheticLayers && (
          <button
            className={`px-2 py-1 ${basemap === "synthetic" ? "bg-primary text-primary-foreground" : ""}`}
            onClick={() => {
              setBasemap("synthetic");
              setTerrain3d(false);
            }}
            title="Representa lo que el escenario asume: suelo uniforme, una sola clase de combustible"
          >
            Esquemático
          </button>
        )}
        <button
          className={`border-l px-2 py-1 disabled:opacity-50 ${terrain3d ? "bg-primary text-primary-foreground" : ""}`}
          onClick={() => setTerrain3d((on) => !on)}
          disabled={basemap === "synthetic"}
          aria-pressed={terrain3d}
          title={
            basemap === "synthetic"
              ? "El escenario sintético asume suelo plano"
              : `Relieve 3D (exagerado ×${TERRAIN_EXAGGERATION.toLocaleString("es")})`
          }
        >
          3D
        </button>
      </div>

      {/* A5 · a run whose isochrones are empty must not look like a broken map. */}
      {isochrones !== null && isochrones.features.length === 0 && (
        <div className="absolute left-1/2 top-4 z-10 max-w-sm -translate-x-1/2 rounded-md border border-amber-500/50 bg-card/95 p-2 text-center text-[11px] shadow-md">
          Esta corrida no produjo isócronas. Se muestra sólo el perímetro FIRMS observado,
          que es la entrada de la simulación, no una predicción.
        </div>
      )}

      {(isochrones || ignitionPerimeter) && (
        <div
          className={`absolute left-2 z-10 rounded-md border bg-card/95 p-2 text-[11px] shadow-md ${
            overlay ? "bottom-20" : "bottom-6"
          }`}
        >
          {/* A4 · the observed seed must stay visually separable from the prediction:
              most of the area a run reports as burned is this polygon, not spread.
              Only shown when there is one — a synthetic playground scenario has no FIRMS
              input, and a legend entry for it invites reading the slab as real ground. */}
          {ignitionPerimeter?.features?.length ? (
            <div className="mb-1 flex items-center gap-2">
              <span
                className="inline-block h-3 w-5 shrink-0 rounded-sm border border-dashed"
                style={{ backgroundColor: "rgba(91,107,122,0.35)", borderColor: "#e2e8f0" }}
              />
              <span>Perímetro FIRMS observado (entrada, t=0)</span>
            </div>
          ) : null}
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-1 w-5 shrink-0 rounded-full"
              style={{ background: "linear-gradient(90deg,#fee08b,#fc8d59,#b30000)" }}
            />
            <span>
              Isócronas previstas 0 → {horizonHours > 0 ? horizonHours.toLocaleString("es", { maximumFractionDigits: 1 }) : 12} h
            </span>
          </div>
          {clock && (
            <>
              <div className="mt-1 flex items-center gap-2">
                <span
                  className="inline-block h-1.5 w-5 shrink-0 rounded-full"
                  style={{ backgroundColor: "#fff4c2", boxShadow: "0 0 4px #fff4c2" }}
                />
                <span>Frente activo</span>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span
                  className="inline-block h-0.5 w-5 shrink-0 rounded-full"
                  style={{ backgroundColor: "#cbd5e1" }}
                />
                <span>Pendiente de quemar</span>
              </div>
            </>
          )}
        </div>
      )}

      {overlay && <div className="absolute bottom-2 left-2 right-2 z-10">{overlay}</div>}
    </div>
  );
}

function windFieldBounds(field: WindField): [number, number, number, number] {
  if (field.kind === "gridded") return field.bounds;
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  for (const [lng, lat] of field.ring) {
    west = Math.min(west, lng);
    south = Math.min(south, lat);
    east = Math.max(east, lng);
    north = Math.max(north, lat);
  }
  return [west, south, east, north];
}

// Adds/updates/removes a MapLibre `image` source + raster layer as `overlay` changes.
function useImageOverlay(
  mapRef: RefObject<MapLibreMap | null>,
  loaded: boolean,
  sourceId: string,
  overlay: ImageOverlay | null,
) {
  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map) return;

    const existing = map.getSource(sourceId) as maplibregl.ImageSource | undefined;

    if (!overlay) {
      if (existing) {
        map.removeLayer(`${sourceId}-layer`);
        map.removeSource(sourceId);
      }
      return;
    }

    if (existing) {
      existing.updateImage({ url: overlay.image_base64, coordinates: overlay.coordinates });
    } else {
      map.addSource(sourceId, {
        type: "image",
        url: overlay.image_base64,
        coordinates: overlay.coordinates,
      });
      map.addLayer({
        id: `${sourceId}-layer`,
        type: "raster",
        source: sourceId,
        paint: { "raster-opacity": 0.75 },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overlay, sourceId, loaded]);
}
