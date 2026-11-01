"""Operational-source adapters for the ensemble POC.

The adapters stop at source-neutral hourly GeoTIFFs (`u10`, `v10`, `t2m`, `rh`).
The existing weather builder then performs the frozen ELMFIRE conversions.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import cast
from urllib.parse import urlencode

import httpx
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

from .weather import (
    gefs_time_axis,
    interpolate_weather_at_valid_times,
    speed_direction_to_uv,
)

GEFS_MEMBERS = ["c00", *[f"p{i:02d}" for i in range(1, 31)]]
GEFS_FILTER = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gefs_atmos_0p25s.pl"
GEFS_ARCHIVE = "https://noaa-gefs-pds.s3.amazonaws.com"
SMN_BASE = "https://smn-ar-wrf.s3-us-west-2.amazonaws.com"
GEFS_REQUIRED_FIELDS = {
    "TMP": "2 m above ground",
    "RH": "2 m above ground",
    "UGRD": "10 m above ground",
    "VGRD": "10 m above ground",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_members(limit: int | None = None) -> list[str]:
    if limit is None:
        return GEFS_MEMBERS.copy()
    if not 1 <= limit <= len(GEFS_MEMBERS):
        raise ValueError("member limit must be between 1 and 31")
    return GEFS_MEMBERS[:limit]


def _member_filename(member: str, cycle_hour: int, forecast_hour: int) -> str:
    prefix = "gec00" if member == "c00" else f"ge{member}"
    return f"{prefix}.t{cycle_hour:02d}z.pgrb2s.0p25.f{forecast_hour:03d}"


def gefs_filter_url(
    cycle: datetime, member: str, forecast_hour: int, bbox: tuple[float, float, float, float]
) -> str:
    if cycle.tzinfo is None or cycle.utcoffset() != UTC.utcoffset(cycle):
        raise ValueError("cycle must be timezone-aware UTC")
    if cycle.hour not in (0, 6, 12, 18) or cycle.minute or cycle.second:
        raise ValueError("GEFS cycle must be exactly 00/06/12/18 UTC")
    if member not in GEFS_MEMBERS:
        raise ValueError(f"unknown GEFS member {member}")
    west, south, east, north = bbox
    filename = _member_filename(member, cycle.hour, forecast_hour)
    query = {
        "file": filename,
        "lev_2_m_above_ground": "on",
        "lev_10_m_above_ground": "on",
        "var_TMP": "on",
        "var_RH": "on",
        "var_UGRD": "on",
        "var_VGRD": "on",
        "subregion": "",
        "leftlon": west,
        "rightlon": east,
        "toplat": north,
        "bottomlat": south,
        "dir": f"/gefs.{cycle:%Y%m%d}/{cycle:%H}/atmos/pgrb2sp25",
    }
    return f"{GEFS_FILTER}?{urlencode(query)}"


def gefs_archive_url(cycle: datetime, member: str, forecast_hour: int) -> str:
    filename = _member_filename(member, cycle.hour, forecast_hour)
    return f"{GEFS_ARCHIVE}/gefs.{cycle:%Y%m%d}/{cycle:%H}/atmos/pgrb2sp25/{filename}"


def _required_grib_range(index_text: str) -> tuple[int, int, list[str]]:
    records = []
    for line in index_text.splitlines():
        parts = line.split(":")
        if len(parts) >= 6:
            records.append((int(parts[1]), parts[3], parts[4], line))
    selected = {
        field: index
        for index, (_, variable, level, _) in enumerate(records)
        for field, wanted_level in GEFS_REQUIRED_FIELDS.items()
        if variable == field and level == wanted_level
    }
    missing = sorted(set(GEFS_REQUIRED_FIELDS) - set(selected))
    if missing:
        raise RuntimeError(f"GEFS index lacks required fields {missing}")
    first = min(selected.values())
    last = max(selected.values())
    if last + 1 >= len(records):
        raise RuntimeError("cannot determine final byte of required GEFS records")
    return records[first][0], records[last + 1][0] - 1, sorted(selected)


def inspect_gefs_archive(
    cycle: datetime,
    forecast_start: datetime,
    horizon_hours: int,
    members: list[str] | None = None,
) -> dict:
    """Confirm the archived members/fields and derive their historical availability."""
    axis = gefs_time_axis(cycle, forecast_start, horizon_hours)
    source_hours = cast(list[int], axis["source_hours"])
    expected = members or GEFS_MEMBERS
    entries, failures = [], []
    with httpx.Client(follow_redirects=True, timeout=60.0) as client:
        for member in expected:
            for hour in source_hours:
                url = gefs_archive_url(cycle, member, hour)
                index_url = f"{url}.idx"
                try:
                    response = client.get(index_url)
                    response.raise_for_status()
                    byte_start, byte_end, fields = _required_grib_range(response.text)
                    last_modified = response.headers.get("last-modified")
                    if last_modified is None:
                        raise RuntimeError("archive response has no Last-Modified header")
                    available_at = parsedate_to_datetime(last_modified).astimezone(UTC)
                    entries.append(
                        {
                            "member": member,
                            "forecast_hour": hour,
                            "valid_at": (cycle + timedelta(hours=hour)).isoformat(),
                            "url": url,
                            "index_url": index_url,
                            "index_etag": response.headers.get("etag", "").strip('"'),
                            "available_at": available_at.isoformat(),
                            "byte_range": [byte_start, byte_end],
                            "required_fields": fields,
                        }
                    )
                except Exception as exc:
                    failures.append(
                        {"member": member, "forecast_hour": hour, "error": str(exc)}
                    )
    if failures:
        raise RuntimeError(
            f"GEFS archive inventory incomplete ({len(failures)} failures): {failures[:5]}"
        )
    available_at = max(datetime.fromisoformat(entry["available_at"]) for entry in entries)
    return {
        "schema_version": 1,
        "source": "NOAA Open Data Dissemination GEFS archive",
        "availability_method": (
            "maximum Last-Modified of every required .idx object; the index is published "
            "after its corresponding GRIB object"
        ),
        "cycle": cycle.isoformat(),
        "cycle_available_at": available_at.isoformat(),
        "forecast_start": forecast_start.isoformat(),
        "perimeter_at": forecast_start.isoformat(),
        "offset_seconds": axis["offset_seconds"],
        "offset_hours": axis["offset_hours"],
        "source_hours": source_hours,
        "source_valid_at": [
            value.isoformat() for value in cast(list[datetime], axis["source_valid_at"])
        ],
        "band_valid_at": [
            value.isoformat() for value in cast(list[datetime], axis["band_valid_at"])
        ],
        "horizon_hours": horizon_hours,
        "expected_members": expected,
        "required_fields": GEFS_REQUIRED_FIELDS,
        "complete": True,
        "entries": entries,
    }


RETRY_STATUS = {429, 500, 502, 503, 504}
RETRY_DELAYS_S = (2.0, 8.0, 30.0)


def _retrying[T](download: Callable[..., T], *args) -> T:
    """Retry transient failures: the NOAA S3 archive answers '503 Slow Down' when several
    members download in parallel (Patriada 09-01 lost 6 of 31 members to it)."""
    for delay in (*RETRY_DELAYS_S, None):
        try:
            return download(*args)
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            transient = (not isinstance(exc, httpx.HTTPStatusError)
                         or exc.response.status_code in RETRY_STATUS)
            if delay is None or not transient:
                raise
            time.sleep(delay)
    raise AssertionError("unreachable")


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as response:
        response.raise_for_status()
        with destination.open("wb") as stream:
            for chunk in response.iter_bytes():
                stream.write(chunk)
    if destination.stat().st_size == 0:
        raise RuntimeError(f"empty download from {url}")


def _download_range(url: str, byte_range: list[int], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Range": f"bytes={byte_range[0]}-{byte_range[1]}"}
    with httpx.stream(
        "GET", url, headers=headers, follow_redirects=True, timeout=120.0
    ) as response:
        response.raise_for_status()
        if response.status_code != 206:
            raise RuntimeError(f"archive ignored byte range for {url}")
        with destination.open("wb") as stream:
            for chunk in response.iter_bytes():
                stream.write(chunk)
    expected = byte_range[1] - byte_range[0] + 1
    if destination.stat().st_size != expected:
        raise RuntimeError(f"incomplete byte-range download from {url}")


def _read_gefs_fields(
    path: Path, bbox: tuple[float, float, float, float] | None = None
) -> tuple[dict[str, np.ndarray], dict]:
    wanted = {"UGRD": "u10", "VGRD": "v10", "TMP": "t2m", "RH": "rh"}
    fields: dict[str, np.ndarray] = {}
    # GDAL otherwise normalizes GRIB temperature from its documented Kelvin to
    # Celsius.  Keep physical source units explicit; derive_moisture expects Kelvin.
    with rasterio.Env(GRIB_NORMALIZE_UNITS="NO"):
        with rasterio.open(path) as src:
            window = None
            if bbox is not None:
                west, south, east, north = bbox
                if src.bounds.left >= 0 and west < 0:
                    west, east = west + 360, east + 360
                window = from_bounds(west, south, east, north, src.transform)
                window = window.round_offsets().round_lengths().intersection(
                    Window(0, 0, src.width, src.height)
                )
            for band in range(1, src.count + 1):
                tags = src.tags(band)
                element = tags.get("GRIB_ELEMENT", "")
                if element in wanted:
                    fields[wanted[element]] = src.read(band, window=window).astype("float32")
            profile = {
                "crs": src.crs or "EPSG:4326",
                "transform": src.window_transform(window) if window is not None else src.transform,
            }
    missing = sorted(set(wanted.values()) - set(fields))
    if missing:
        raise RuntimeError(f"{path} lacks required fields {missing}")
    return fields, profile


def _write_stack(path: Path, cube: np.ndarray, profile: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=cube.shape[1],
        width=cube.shape[2],
        count=cube.shape[0],
        dtype="float32",
        nodata=-9999.0,
        compress="deflate",
        predictor=3,
        crs=profile["crs"],
        transform=profile["transform"],
    ) as dst:
        dst.write(cube.astype("float32"))


def download_gefs_member(
    cycle: datetime,
    member: str,
    bbox: tuple[float, float, float, float],
    horizon_hours: int,
    output_dir: Path,
    *,
    forecast_start: datetime,
    inventory: dict | None = None,
) -> dict:
    """Download filtered 3-hourly GEFS fields and emit hourly source-neutral rasters."""
    axis = gefs_time_axis(cycle, forecast_start, horizon_hours)
    source_hours = cast(list[int], axis["source_hours"])
    source_valid_at = cast(list[datetime], axis["source_valid_at"])
    band_valid_at = cast(list[datetime], axis["band_valid_at"])
    archive_entries = {
        (entry["member"], entry["forecast_hour"]): entry
        for entry in (inventory or {}).get("entries", [])
    }
    if inventory is not None:
        if inventory.get("cycle") != cycle.isoformat():
            raise ValueError("inventory cycle does not match requested cycle")
        if inventory.get("forecast_start") != forecast_start.isoformat():
            raise ValueError("inventory forecast_start does not match requested start")
        if datetime.fromisoformat(inventory["cycle_available_at"]) > forecast_start:
            raise ValueError("GEFS cycle was not completely available at forecast_start")
    raw_dir = output_dir / "source"
    cubes: dict[str, list[np.ndarray]] = {name: [] for name in ("u10", "v10", "t2m", "rh")}
    sources, profile = [], None
    for hour in source_hours:
        path = raw_dir / f"f{hour:03d}.grib2"
        entry = archive_entries.get((member, hour))
        if inventory is not None and entry is None:
            raise RuntimeError(f"inventory lacks {member} f{hour:03d}; no substitution")
        if entry is not None:
            url = entry["url"]
            _retrying(_download_range, url, entry["byte_range"], path)
        else:
            url = gefs_filter_url(cycle, member, hour, bbox)
            _retrying(_download, url, path)
        fields, current_profile = _read_gefs_fields(path, bbox if entry is not None else None)
        profile = profile or current_profile
        if current_profile != profile or any(
            value.shape != fields["u10"].shape for value in fields.values()
        ):
            raise RuntimeError(f"GEFS grid changed at member={member} f{hour:03d}")
        for name in cubes:
            cubes[name].append(fields[name])
        source_row = {
            "forecast_hour": hour,
            "valid_at": (cycle + timedelta(hours=hour)).isoformat(),
            "url": url,
            "file": str(path),
            "sha256": sha256(path),
        }
        if entry is not None:
            source_row |= {
                "index_url": entry["index_url"],
                "index_etag": entry["index_etag"],
                "available_at": entry["available_at"],
                "byte_range": entry["byte_range"],
            }
        sources.append(source_row)
    if profile is None:
        raise RuntimeError(f"GEFS member {member} produced no source fields")
    hourly = interpolate_weather_at_valid_times(
        np.stack(cubes["u10"]),
        np.stack(cubes["v10"]),
        np.stack(cubes["t2m"]),
        np.stack(cubes["rh"]),
        source_valid_at,
        band_valid_at,
    )
    for name, cube in hourly.items():
        _write_stack(output_dir / f"{name}.tif", cube, profile)
    manifest = {
        "source": "NOAA NCEP GEFS pgrb2s 0.25 degree",
        "cycle": cycle.isoformat(),
        "cycle_available_at": (inventory or {}).get("cycle_available_at"),
        "forecast_start": forecast_start.isoformat(),
        "perimeter_at": forecast_start.isoformat(),
        "offset_seconds": axis["offset_seconds"],
        "offset_hours": axis["offset_hours"],
        "member": member,
        "source_hours": source_hours,
        "source_valid_at": [value.isoformat() for value in source_valid_at],
        "band_valid_at": [value.isoformat() for value in band_valid_at],
        "bbox_wgs84": bbox,
        "transformations": [
            (
                "NOAA archive GRIB byte-range extraction and AOI crop"
                if inventory is not None
                else "NOMADS variable/level/bbox filter"
            ),
            "linear temporal interpolation on U/V/T/RH at absolute UTC valid times",
        ],
        "files": sources,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def smn_object_url(cycle: datetime, forecast_hour: int) -> str:
    filename = f"WRFDETAR_01H_{cycle:%Y%m%d}_{cycle:%H}_{forecast_hour:03d}.nc"
    return f"{SMN_BASE}/DATA/WRF/DET/{cycle:%Y/%m/%d/%H}/{filename}"


def download_smn_wrf(
    cycle: datetime,
    bbox: tuple[float, float, float, float],
    horizon_hours: int,
    output_dir: Path,
) -> dict:
    """Prototype the independent regional scenario from hourly SMN WRF NetCDF files."""
    west, south, east, north = bbox
    cubes: dict[str, list[np.ndarray]] = {name: [] for name in ("u10", "v10", "t2m", "rh")}
    sources, profile, expected_window = [], None, None
    for hour in range(horizon_hours + 1):
        url = smn_object_url(cycle, hour)
        path = output_dir / "source" / Path(url).name
        _download(url, path)
        subdataset = lambda name: f"netcdf:{path}:{name}"  # noqa: E731
        with rasterio.open(subdataset("T2")) as reference:
            if reference.crs is None:
                raise RuntimeError(f"{path}: T2 has no native Lambert CRS")
            native_bounds = transform_bounds(
                "EPSG:4326", reference.crs, west, south, east, north, densify_pts=21
            )
            current_window = from_bounds(*native_bounds, reference.transform)
            current_window = current_window.round_offsets().round_lengths()
            current_window = current_window.intersection(
                Window(0, 0, reference.width, reference.height)
            )
            window_key = (
                int(current_window.row_off),
                int(current_window.col_off),
                int(current_window.height),
                int(current_window.width),
            )
            expected_window = expected_window or window_key
            if window_key != expected_window:
                raise RuntimeError("SMN WRF AOI window changed between hours")
            t2m = reference.read(1, window=current_window).astype("float32") + 273.15
            if profile is None:
                profile = {
                    "crs": reference.crs,
                    "transform": reference.window_transform(current_window),
                }
        fields = {}
        for variable in ("HR2", "magViento10", "dirViento10"):
            try:
                with rasterio.open(subdataset(variable)) as src:
                    fields[variable] = src.read(1, window=current_window).astype("float32")
            except rasterio.errors.RasterioIOError as exc:
                raise RuntimeError(f"{path} lacks SMN variable {variable}") from exc
        u, v = speed_direction_to_uv(fields["magViento10"], fields["dirViento10"])
        values = {"u10": u, "v10": v, "t2m": t2m, "rh": fields["HR2"]}
        for name in cubes:
            cubes[name].append(values[name].astype("float32"))
        sources.append(
            {"forecast_hour": hour, "url": url, "file": str(path), "sha256": sha256(path)}
        )
    if profile is None:
        raise RuntimeError("SMN WRF produced no source fields")
    for name, bands in cubes.items():
        _write_stack(output_dir / f"{name}.tif", np.stack(bands), profile)
    manifest = {
        "source": "escenario regional SMN WRF",
        "included_in_gefs_denominator": False,
        "cycle": cycle.isoformat(),
        "hours": list(range(horizon_hours + 1)),
        "bbox_wgs84": bbox,
        "transformations": [
            "AOI rectangular crop on native Lambert grid",
            "Celsius to Kelvin",
            "speed/direction to U/V",
        ],
        "files": sources,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
