"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import maplibregl, { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// Los Alerces National Park, Patagonia — matches the AOI these simulations run over.
const INITIAL_CENTER: [number, number] = [-71.8, -42.7];
const INITIAL_ZOOM = 10;

const FIRES_SOURCE_ID = "active-fires";
const ISOCHRONES_SOURCE_ID = "isochrones";
const TOA_SOURCE_ID = "time-of-arrival-overlay";
const FLIN_SOURCE_ID = "fireline-intensity-overlay";

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

export type RasterOverlayData = {
  image_base64: string;
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
  value_range: [number, number];
  unit: string;
};

export function FireMap({
  activeFires,
  isochrones,
  timeOfArrivalOverlay,
  firelineIntensityOverlay,
}: {
  activeFires: GeoJSON.FeatureCollection | null;
  isochrones: GeoJSON.FeatureCollection | null;
  timeOfArrivalOverlay: RasterOverlayData | null;
  firelineIntensityOverlay: RasterOverlayData | null;
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
    const map = mapRef.current;
    if (!loadedRef.current || !map) return;
    map.setLayoutProperty("street", "visibility", basemap === "street" ? "visible" : "none");
    map.setLayoutProperty("satellite", "visibility", basemap === "satellite" ? "visible" : "none");
  }, [basemap]);

  useImageOverlay(mapRef, loadedRef, TOA_SOURCE_ID, timeOfArrivalOverlay);
  useImageOverlay(mapRef, loadedRef, FLIN_SOURCE_ID, firelineIntensityOverlay);

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
    </div>
  );
}

// Adds/updates/removes a MapLibre `image` source + raster layer as `overlay` changes.
function useImageOverlay(
  mapRef: RefObject<MapLibreMap | null>,
  loadedRef: RefObject<boolean>,
  sourceId: string,
  overlay: RasterOverlayData | null,
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
