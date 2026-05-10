"""
Converts ELMFIRE output shapefiles to GeoJSON for the API.

ELMFIRE produces hourly_isochrones.shp (Shapefile). This module reads it and
returns a GeoJSON FeatureCollection that can be stored in PostGIS or served directly.

TODO Sprint siguiente: implement using geopandas.
"""
from pathlib import Path


def shapefile_to_geojson(shp_path: Path) -> dict:
    """Return a GeoJSON FeatureCollection from an ELMFIRE isochrones shapefile."""
    raise NotImplementedError("isochrone_converter: sprint siguiente")
