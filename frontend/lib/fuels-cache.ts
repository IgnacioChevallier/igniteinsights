import type { ImageOverlay } from "@/components/fire-map";
import { FUELS_SOURCES, type FuelsSource } from "@/lib/real-run";

export type FuelClass = {
  fbfm40: number;
  label: string;
  color: string;
  source_classes: string[];
  pixel_count: number;
  area_ha: number;
  share: number;
};

export type FuelsMap = ImageOverlay & {
  source_id: FuelsSource;
  source: string;
  available_sources: FuelsSource[];
  classes: FuelClass[];
  total_area_ha: number;
};

// The payload contains the already-rendered base64 PNG, so caching the promise avoids both
// a second HTTP transfer and a second raster render when the FuelsPanel mounts. Rejected
// requests are evicted: a source that is built by a later ingestion must remain retryable.
const requests = new Map<FuelsSource, Promise<FuelsMap>>();

export function loadFuelsMap(source: FuelsSource): Promise<FuelsMap> {
  const cached = requests.get(source);
  if (cached) return cached;

  const request = fetch(`/api/fuels?source=${source}`, { cache: "no-store" })
    .then(async (res) => {
      const envelope = await res.json();
      if (!res.ok || !envelope.data) {
        throw new Error(envelope.detail ?? envelope.error?.message ?? "Sin datos");
      }
      return envelope.data as FuelsMap;
    })
    .catch((error) => {
      if (requests.get(source) === request) requests.delete(source);
      throw error;
    });

  requests.set(source, request);
  return request;
}

/**
 * Warm the configured map first, then the remaining built sources one at a time. Sequential
 * work matters here: each response colorizes a 16 MB raster, and running all three together
 * would steal CPU from the simulation map the operator is currently looking at.
 */
export async function preloadFuelsMaps(preferred: FuelsSource): Promise<void> {
  let candidates = FUELS_SOURCES.map(({ id }) => id);
  try {
    const primary = await loadFuelsMap(preferred);
    candidates = primary.available_sources;
  } catch {
    // The preferred source may not have been built yet. Probe the others so the tab can
    // still open instantly on whichever static products are available.
  }

  for (const source of candidates) {
    if (source === preferred) continue;
    try {
      await loadFuelsMap(source);
    } catch {
      // Missing optional products stay disabled once the first successful payload reports
      // available_sources. A future ingestion can retry because failures are not cached.
    }
  }
}
