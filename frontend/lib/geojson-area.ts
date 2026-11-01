const EARTH_RADIUS_M = 6_378_137;
const M2_PER_HA = 10_000;

type Position = number[];
type Ring = Position[];

function radians(value: number) {
  return (value * Math.PI) / 180;
}

/** Spherical ring area using the Chamberlain-Duquette approximation. */
function ringAreaM2(ring: Ring) {
  if (ring.length < 3) return 0;
  let sum = 0;
  for (let index = 0; index < ring.length; index += 1) {
    const current = ring[index];
    const next = ring[(index + 1) % ring.length];
    sum +=
      radians(next[0] - current[0]) *
      (2 + Math.sin(radians(current[1])) + Math.sin(radians(next[1])));
  }
  return Math.abs((sum * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2);
}

function polygonAreaM2(coordinates: Ring[]) {
  if (!coordinates.length) return 0;
  const holes = coordinates
    .slice(1)
    .reduce((sum, ring) => sum + ringAreaM2(ring), 0);
  return Math.max(ringAreaM2(coordinates[0]) - holes, 0);
}

function geometryAreaM2(geometry: GeoJSON.Geometry | null): number {
  if (!geometry) return 0;
  if (geometry.type === "Polygon") return polygonAreaM2(geometry.coordinates);
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.reduce((sum, polygon) => sum + polygonAreaM2(polygon), 0);
  }
  if (geometry.type === "GeometryCollection") {
    return geometry.geometries.reduce((sum, child) => sum + geometryAreaM2(child), 0);
  }
  return 0;
}

export function geoJsonAreaHa(collection: GeoJSON.FeatureCollection | null) {
  if (!collection) return null;
  const areaM2 = collection.features.reduce(
    (sum, feature) => sum + geometryAreaM2(feature.geometry),
    0,
  );
  return areaM2 > 0 ? areaM2 / M2_PER_HA : null;
}

/** Area of the latest cumulative isochrone available at or before the selected horizon. */
export function isochroneAreaHa(
  collection: GeoJSON.FeatureCollection | null,
  horizonHours: number,
) {
  if (!collection) return null;
  let latest = -Infinity;
  for (const feature of collection.features) {
    const arrival = Number(feature.properties?.arrival_hours);
    if (Number.isFinite(arrival) && arrival <= horizonHours && arrival > latest) latest = arrival;
  }
  if (!Number.isFinite(latest)) return null;
  return geoJsonAreaHa({
    ...collection,
    features: collection.features.filter(
      (feature) => Number(feature.properties?.arrival_hours) === latest,
    ),
  });
}
