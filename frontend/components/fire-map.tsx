"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import maplibregl, { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// Los Alerces National Park, Patagonia — matches the AOI these simulations run over.
const INITIAL_CENTER: [number, number] = [-71.8, -42.7];
const INITIAL_ZOOM = 10;

const FIRES_SOURCE_ID = "active-fires";
const ISOCHRONES_SOURCE_ID = "isochrones";
const IGNITION_SOURCE_ID = "ignition-perimeter";
const TOA_SOURCE_ID = "time-of-arrival-overlay";
const FLIN_SOURCE_ID = "fireline-intensity-overlay";
const FUELS_SOURCE_ID = "fuels-overlay";

// Two tokenless basemaps, both loaded up front and toggled via layout.visibility
// (not map.setStyle(), which would wipe every custom source/layer below).
const STREET_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const SATELLITE_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

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
  },
  layers: [
    { id: "street", type: "raster", source: "street", layout: { visibility: "none" } },
    { id: "satellite", type: "raster", source: "satellite" },
  ],
};

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

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
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const loadedRef = useRef(false);
  const [basemap, setBasemap] = useState<"street" | "satellite">("satellite");

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
      map.addLayer({
        id: `${IGNITION_SOURCE_ID}-outline`,
        type: "line",
        source: IGNITION_SOURCE_ID,
        paint: { "line-color": "#334155", "line-width": 1.5, "line-dasharray": [3, 2] },
      });

      map.addSource(ISOCHRONES_SOURCE_ID, { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: `${ISOCHRONES_SOURCE_ID}-line`,
        type: "line",
        source: ISOCHRONES_SOURCE_ID,
        paint: {
          "line-color": [
            "interpolate",
            ["linear"],
            ["coalesce", ["get", "arrival_hours"], -1],
            -1,
            "#999999",
            0,
            "#fee08b",
            6,
            "#fc8d59",
            12,
            "#b30000",
          ],
          "line-width": 2,
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

      for (const layerId of [`${ISOCHRONES_SOURCE_ID}-line`, `${FIRES_SOURCE_ID}-circle`]) {
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

      loadedRef.current = true;
      if (activeFires) (map.getSource(FIRES_SOURCE_ID) as maplibregl.GeoJSONSource).setData(activeFires);
      if (isochrones) (map.getSource(ISOCHRONES_SOURCE_ID) as maplibregl.GeoJSONSource).setData(isochrones);
      if (ignitionPerimeter)
        (map.getSource(IGNITION_SOURCE_ID) as maplibregl.GeoJSONSource).setData(ignitionPerimeter);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!loadedRef.current || !mapRef.current) return;
    const source = mapRef.current.getSource(FIRES_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    source?.setData(activeFires ?? EMPTY_FC);
  }, [activeFires]);

  useEffect(() => {
    if (!loadedRef.current || !mapRef.current) return;
    const source = mapRef.current.getSource(ISOCHRONES_SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined;
    source?.setData(isochrones ?? EMPTY_FC);
  }, [isochrones]);

  useEffect(() => {
    if (!loadedRef.current || !mapRef.current) return;
    const source = mapRef.current.getSource(IGNITION_SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined;
    source?.setData(ignitionPerimeter ?? EMPTY_FC);
  }, [ignitionPerimeter]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loadedRef.current || !map || !fitTo?.features?.length) return;
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
  }, [fitTo]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loadedRef.current || !map) return;
    map.setLayoutProperty("street", "visibility", basemap === "street" ? "visible" : "none");
    map.setLayoutProperty("satellite", "visibility", basemap === "satellite" ? "visible" : "none");
  }, [basemap]);

  useImageOverlay(mapRef, loadedRef, TOA_SOURCE_ID, timeOfArrivalOverlay);
  useImageOverlay(mapRef, loadedRef, FLIN_SOURCE_ID, firelineIntensityOverlay);
  useImageOverlay(mapRef, loadedRef, FUELS_SOURCE_ID, fuelsOverlay);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
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
      </div>

      {(isochrones || ignitionPerimeter) && (
      <div className="absolute bottom-6 left-2 z-10 rounded-md border bg-card/95 p-2 text-[11px] shadow-md">
        <div className="mb-1 flex items-center gap-2">
          <span
            className="inline-block h-3 w-5 shrink-0 rounded-sm border border-dashed"
            style={{ backgroundColor: "rgba(91,107,122,0.35)", borderColor: "#334155" }}
          />
          <span>Perímetro FIRMS observado (entrada)</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="inline-block h-1 w-5 shrink-0 rounded-full"
            style={{ background: "linear-gradient(90deg,#fee08b,#fc8d59,#b30000)" }}
          />
          <span>Isócronas previstas 0 → 12 h</span>
        </div>
      </div>
      )}
    </div>
  );
}

// Adds/updates/removes a MapLibre `image` source + raster layer as `overlay` changes.
function useImageOverlay(
  mapRef: RefObject<MapLibreMap | null>,
  loadedRef: RefObject<boolean>,
  sourceId: string,
  overlay: ImageOverlay | null,
) {
  useEffect(() => {
    const map = mapRef.current;
    if (!loadedRef.current || !map) return;

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
  }, [overlay, sourceId]);
}
