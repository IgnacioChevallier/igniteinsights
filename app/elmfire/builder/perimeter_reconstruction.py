"""
Reconstructs contiguous burn perimeters from scattered FIRMS/VIIRS detection points.

VIIRS delivers point samples of the *actively flaming* fire front at discrete
overpass times (~2/day) — never the burned area itself. Interior cells that already
burned are cold and are not re-detected, so a moving fire leaves scattered arcs and
patches along its path. Uniformly buffering each point cannot reconstruct the
perimeter: on real Los Alerces data (633 detections, 48 h window) fusing everything
into one polygon by buffer alone needs a 4.4 km radius (max MST edge 8.8 km), which
inflates the ignition to ~32 kha versus a ~4 kha real fire.

Instead this module separates the two inferences a uniform buffer conflates:
  1. "same fire event"  → single-linkage distance clustering (eps),
  2. "interior burned"  → concave hull per cluster, padded by half a VIIRS pixel.

Clusters too small for a meaningful hull are kept as individually buffered points —
isolated detections are often legitimate spot fires and must not be dropped or
absorbed into a distant front.
"""
import logging

import shapely
from shapely.geometry import MultiPoint, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

# VIIRS I-band nominal pixel width; a detection means "fire somewhere in this pixel",
# so reconstructed shapes are padded by half a pixel to cover the sensor footprint.
VIIRS_PIXEL_M = 375.0

# Single-linkage linking distance: detections closer than this are the same event.
# Calibrated on the real 2026-02 Los Alerces window: 1500 m yields 8-14 clusters
# dominated by a few large fronts, and does NOT bridge the ~3-4 km wide lake between
# the two burning shores. Larger eps risks fusing genuinely separate fires.
_CLUSTER_EPS_M = 1500.0

# shapely.concave_hull concavity ratio (0 = tightest, 1 = convex hull). 0.4 fills
# the revisit gaps inside one front without swallowing large unburned concavities
# the way a convex hull would (e.g. a C-shaped fire wrapping a lake shore).
_HULL_RATIO = 0.4

# Below this many points a concave hull is meaningless; fall back to point buffers.
_MIN_HULL_POINTS = 4

# Duplicate-detection collapse grid: FIRMS re-ingestions store the same detection
# multiple times; positions within this tolerance are one detection.
_DEDUP_GRID_M = 10.0


def reconstruct_burn_polygon(
    points_xy: list[tuple[float, float]],
    point_buffer_m: float = VIIRS_PIXEL_M,
    cluster_eps_m: float = _CLUSTER_EPS_M,
    hull_ratio: float = _HULL_RATIO,
) -> BaseGeometry:
    """
    Build a burn (Multi)Polygon from projected detection points (meters, e.g. UTM).

    Args:
        points_xy: detection coordinates in a projected CRS (meters)
        point_buffer_m: radius for detections in clusters too small to hull
        cluster_eps_m: single-linkage distance defining "same fire event"
        hull_ratio: shapely.concave_hull ratio (0 tight .. 1 convex)

    Returns:
        Polygon or MultiPolygon. Multiple parts mean genuinely separate fires
        (or spot fires), not fragmentation artifacts.
    """
    deduped = _dedup(points_xy)
    clusters = _cluster(deduped, cluster_eps_m)

    cluster_polygons = []
    for cluster in clusters:
        if len(cluster) >= _MIN_HULL_POINTS:
            hull = shapely.concave_hull(
                MultiPoint(cluster), ratio=hull_ratio, allow_holes=False
            )
            # Half-pixel padding covers the sensor footprint and also repairs
            # degenerate hulls (near-collinear scan-line points collapse to a
            # zero-area LineString).
            cluster_polygons.append(hull.buffer(VIIRS_PIXEL_M / 2))
        else:
            cluster_polygons.extend(
                Point(x, y).buffer(point_buffer_m) for x, y in cluster
            )

    burn_polygon = unary_union(cluster_polygons)
    n_parts = len(burn_polygon.geoms) if burn_polygon.geom_type == "MultiPolygon" else 1
    logger.info(
        "Perimeter reconstruction: %d detections (%d unique) → %d clusters → "
        "%d polygon(s), %.0f ha",
        len(points_xy),
        len(deduped),
        len(clusters),
        n_parts,
        burn_polygon.area / 1e4,
    )
    return burn_polygon


def _dedup(points_xy: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Collapse points that coincide within _DEDUP_GRID_M (re-ingested duplicates)."""
    seen: dict[tuple[int, int], tuple[float, float]] = {}
    for x, y in points_xy:
        key = (round(x / _DEDUP_GRID_M), round(y / _DEDUP_GRID_M))
        seen.setdefault(key, (x, y))
    return list(seen.values())


def _cluster(
    points_xy: list[tuple[float, float]], eps_m: float
) -> list[list[tuple[float, float]]]:
    """
    Single-linkage clustering at linking distance eps_m, computed geometrically:
    two points are in the same cluster iff their eps/2 disks form one connected
    union component. Avoids an sklearn dependency.
    """
    union = unary_union([Point(x, y).buffer(eps_m / 2, quad_segs=8) for x, y in points_xy])
    parts = list(union.geoms) if union.geom_type == "MultiPolygon" else [union]

    tree = shapely.STRtree([Point(x, y) for x, y in points_xy])
    clusters = []
    for part in parts:
        idx = tree.query(part, predicate="intersects")
        clusters.append([points_xy[i] for i in idx])
    return clusters
