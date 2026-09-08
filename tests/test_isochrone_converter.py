"""Isochrone GeoJSON conversion: arrival time comes from the contour attribute
gdal_contour writes (-a arrival_s), never from resampling the raster."""
import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import LineString, Polygon
from shapely.geometry import shape as shapely_shape

from app.postprocessing.isochrone_converter import (
    isochrones_to_geojson,
    shapefile_to_geojson,
)


def _write(tmp_path, gdf, name="hourly_isochrones.shp"):
    path = tmp_path / name
    gdf.to_file(str(path))
    return path


def test_missing_shapefile_is_an_empty_collection(tmp_path):
    assert isochrones_to_geojson(tmp_path / "nope.shp") == {
        "type": "FeatureCollection",
        "features": [],
    }


def test_arrival_hours_derived_from_the_contour_attribute(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"arrival_s": [3600.0, 43200.0], "geometry": [
            LineString([(500000, 5250000), (500100, 5250100)]),
            LineString([(500200, 5250200), (500300, 5250300)]),
        ]},
        crs="EPSG:32719",
    )
    fc = isochrones_to_geojson(_write(tmp_path, gdf))
    hours = sorted(f["properties"]["arrival_hours"] for f in fc["features"])
    assert hours == [1.0, 12.0]


def test_shapefile_without_the_attribute_yields_unknown_not_a_guess(tmp_path):
    """Pre-`-a` runs must render as unknown rather than being assigned a fabricated
    time — the old midpoint-resampling put ~16% of contours at hour 0."""
    gdf = gpd.GeoDataFrame(
        {"ID": [0], "geometry": [LineString([(500000, 5250000), (500100, 5250100)])]},
        crs="EPSG:32719",
    )
    props = isochrones_to_geojson(_write(tmp_path, gdf))["features"][0]["properties"]
    assert props["arrival_s"] is None
    assert props["arrival_hours"] is None


def test_reprojects_to_wgs84(tmp_path):
    """Domain corner of a real Los Alerces run (elmfire.data XLL/YLLCORNER) must
    land inside the configured AOI once reprojected."""
    gdf = gpd.GeoDataFrame(
        {
            "arrival_s": [0.0],
            "geometry": [LineString([(253479.65, 5245943.28), (253579, 5246043)])],
        },
        crs="EPSG:32719",
    )
    fc = isochrones_to_geojson(_write(tmp_path, gdf))
    lon, lat = fc["features"][0]["geometry"]["coordinates"][0]
    # Slightly wider than the configured AOI: the UTM domain is the bounding
    # rectangle of the reprojected lat/lon bbox, so it overhangs the corners.
    assert -72.1 < lon < -71.4
    assert -43.0 < lat < -42.4


def test_ignition_polygon_passes_through_untouched(tmp_path):
    """ignicion.shp goes through the bare converter — no arrival fields invented."""
    gdf = gpd.GeoDataFrame(
        {"id": [1], "geometry": [
            Polygon([(500000, 5250000), (501000, 5250000), (501000, 5251000), (500000, 5251000)])
        ]},
        crs="EPSG:32719",
    )
    fc = shapefile_to_geojson(_write(tmp_path, gdf, "ignicion.shp"))
    assert len(fc["features"]) == 1
    assert "arrival_hours" not in fc["features"][0]["properties"]


def test_missing_crs_is_an_error_not_a_silent_wrong_projection(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"arrival_s": [0.0], "geometry": [LineString([(0, 0), (1, 1)])]}, crs=None
    )
    path = tmp_path / "nocrs.shp"
    gdf.to_file(str(path))
    (tmp_path / "nocrs.prj").unlink(missing_ok=True)
    with pytest.raises(ValueError, match="no CRS"):
        isochrones_to_geojson(path)


# ── Burned area is polygonised from the raster, never from the contour lines ───────────


def _toa_with_a_hole(tmp_path, size=40, hole_radius=6):
    """A time-of-arrival raster whose fire wraps around an unburnable disc.

    ELMFIRE's convention: nodata = 0, so an unburned cell simply holds 0. The disc is what
    a lake, a rock outcrop or a road looks like to this code.
    """
    rows, cols = np.mgrid[0:size, 0:size]
    centre = (size - 1) / 2.0
    dist = np.hypot(rows - centre, cols - centre)
    toa = np.where(dist <= size * 0.45, dist * 200.0 + 1.0, 0.0).astype("float32")
    hole = np.hypot(rows - centre - size * 0.2, cols - centre) <= hole_radius
    toa[hole] = 0.0

    path = tmp_path / "time_of_arrival_0000001_0007200.tif"
    with rasterio.open(
        path, "w", driver="GTiff", height=size, width=size, count=1,
        dtype="float32", crs="EPSG:32719", nodata=0.0,
        transform=from_origin(500000, 5300000, 30, 30),
    ) as dst:
        dst.write(toa, 1)
    return path, toa, hole


def _contours_with_levels(tmp_path, levels):
    """A stand-in for the runner's hourly_isochrones.shp: only its levels are used."""
    gdf = gpd.GeoDataFrame(
        {"arrival_s": list(levels)},
        geometry=[LineString([(500000, 5300000), (500100, 5300100)]) for _ in levels],
        crs="EPSG:32719",
    )
    path = tmp_path / "hourly_isochrones.shp"
    gdf.to_file(path)
    return path


def test_unburnable_ground_inside_the_front_is_a_hole_not_burned_area(tmp_path):
    """The bug this replaced: an open contour skirting a lake got closed with a chord, and
    the fill painted the lake. On the real 6 km scenario that was 1022 water cells."""
    toa_path, toa, hole = _toa_with_a_hole(tmp_path)
    shp = _contours_with_levels(tmp_path, [3600.0, 7200.0])

    geojson = isochrones_to_geojson(shp, toa_path)
    assert [f["geometry"]["type"] for f in geojson["features"]] == ["Polygon", "Polygon"]

    with rasterio.open(toa_path) as src:
        transform, shape = src.transform, src.shape
    # Back onto the raster grid, so the comparison is cell for cell rather than by area.
    final = (
        gpd.GeoSeries([shapely_shape(geojson["features"][-1]["geometry"])], crs="EPSG:4326")
        .to_crs("EPSG:32719")
        .iloc[0]
    )
    painted = rasterize([(final, 1)], out_shape=shape, transform=transform, fill=0).astype(bool)
    assert not (painted & hole).any(), "unburnable ground was painted as burned"
    assert painted.sum() == (toa > 0).sum(), "burned area must equal the cells that burned"


def test_no_speck_features(tmp_path):
    """The dots on the map were contour fragments — three or four vertices each. A
    polygonised mask cannot produce them: every ring follows real cell edges."""
    toa_path, _, _ = _toa_with_a_hole(tmp_path)
    shp = _contours_with_levels(tmp_path, [3600.0, 7200.0])
    for feature in isochrones_to_geojson(shp, toa_path)["features"]:
        assert len(feature["geometry"]["coordinates"][0]) > 8


def test_falls_back_to_contour_lines_without_a_raster(tmp_path):
    """Old runs kept their rendering rather than going blank."""
    shp = _contours_with_levels(tmp_path, [3600.0])
    geojson = isochrones_to_geojson(shp, None)
    assert geojson["features"][0]["geometry"]["type"] == "LineString"
    assert geojson["features"][0]["properties"]["arrival_hours"] == 1.0


def _axis_aligned_fraction(ring) -> float:
    """Share of boundary segments that are exactly horizontal or vertical.

    Polygonising a raster mask traces cell edges, so this is ~1.0 for a staircase and
    near 0 once the ring has been smoothed.
    """
    pts = np.asarray(ring)
    d = np.diff(pts, axis=0)
    axis_aligned = np.isclose(d[:, 0], 0) | np.isclose(d[:, 1], 0)
    return float(axis_aligned.mean())


def test_boundaries_are_smooth_not_a_staircase_of_cell_edges(tmp_path):
    """The regression this guards: switching from contour lines to a polygonised mask
    made every boundary a run of right angles at the 30 m cell size, which read as
    rectangular corners on the map."""
    toa_path, _, _ = _toa_with_a_hole(tmp_path)
    shp = _contours_with_levels(tmp_path, [3600.0, 7200.0])

    for feature in isochrones_to_geojson(shp, toa_path)["features"]:
        for ring in feature["geometry"]["coordinates"]:
            assert _axis_aligned_fraction(ring) < 0.15, "boundary is still a cell staircase"


def test_bands_stay_nested_after_smoothing(tmp_path):
    """Smoothing each band on its own let an inner one poke outside the next one out,
    drawing a hairline where the stacked bands overlap."""
    toa_path, _, _ = _toa_with_a_hole(tmp_path)
    shp = _contours_with_levels(tmp_path, [3600.0, 7200.0, 10800.0])

    bands = [
        shapely_shape(f["geometry"]) for f in isochrones_to_geojson(shp, toa_path)["features"]
    ]
    for inner, outer in zip(bands, bands[1:]):
        assert inner.difference(outer).area == pytest.approx(0.0, abs=1e-12)
