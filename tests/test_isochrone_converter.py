"""Isochrone GeoJSON conversion: arrival time comes from the contour attribute
gdal_contour writes (-a arrival_s), never from resampling the raster."""
import geopandas as gpd
import pytest
from shapely.geometry import LineString, Polygon

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
