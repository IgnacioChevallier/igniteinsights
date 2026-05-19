import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .errors import GFSCycleResolutionError, GFSDownloadError
from .schemas import GFSCycleInfo, GFSVariableMetadata

logger = logging.getLogger(__name__)

# GRIB2 search strings and output variable names
# Each entry: (search_string, asset_type, xarray_field_name)
VARIABLES: dict[str, tuple[str, str, str]] = {
    "u10": (":UGRD:10 m above ground:", "gfs_u10", "u10"),
    "v10": (":VGRD:10 m above ground:", "gfs_v10", "v10"),
    "t2m": (":TMP:2 m above ground:", "gfs_t2m", "t2m"),
    "rh":  (":RH:2 m above ground:", "gfs_rh", "r2"),
}

# GFS cycles are published at 00, 06, 12, 18 UTC.
# We try cycles from most-recent backwards (NOMADS keeps ~48 h of availability).
CYCLE_HOURS = [18, 12, 6, 0]
MAX_LOOKBACK_DAYS = 2


class GFSClient:
    def resolve_latest_cycle(self) -> GFSCycleInfo:
        try:
            from herbie import Herbie
        except ImportError as exc:
            raise GFSCycleResolutionError("herbie-data is not installed") from exc

        now_utc = datetime.now(UTC)
        for days_back in range(MAX_LOOKBACK_DAYS + 1):
            candidate_date = now_utc - timedelta(days=days_back)
            for cycle_hour in CYCLE_HOURS:
                candidate = candidate_date.replace(
                    hour=cycle_hour, minute=0, second=0, microsecond=0
                )
                if candidate > now_utc - timedelta(hours=4):
                    # GFS data typically available ~4 h after cycle time
                    continue
                date_str = candidate.strftime("%Y-%m-%d %H:%M")
                try:
                    H = Herbie(date_str, model="gfs", product="pgrb2.0p25", fxx=0, verbose=False)
                    H.grib  # triggers availability check
                    logger.info("Resolved GFS cycle: %s %02dz", candidate.date(), cycle_hour)
                    return GFSCycleInfo(
                        date=candidate.strftime("%Y-%m-%d"),
                        cycle_hour=cycle_hour,
                        fxx=0,
                    )
                except Exception:
                    logger.debug("GFS cycle %s %02dz not available, trying earlier", candidate.date(), cycle_hour)
                    continue

        raise GFSCycleResolutionError(
            f"No GFS cycle available in the last {MAX_LOOKBACK_DAYS} days"
        )

    def download_variable(
        self,
        cycle: GFSCycleInfo,
        var_key: str,
        bbox_west: float,
        bbox_south: float,
        bbox_east: float,
        bbox_north: float,
        output_path: Path,
    ) -> GFSVariableMetadata:
        try:
            import rioxarray  # noqa: F401 — registers .rio accessor on xarray
            from herbie import Herbie
        except ImportError as exc:
            raise GFSDownloadError(f"Required library not installed: {exc}") from exc

        search_string, asset_type, field_name = VARIABLES[var_key]
        cycle_str = f"{cycle.date.replace('-', '')}{cycle.cycle_hour:02d}"
        date_str = f"{cycle.date} {cycle.cycle_hour:02d}:00"

        logger.info("Downloading GFS variable=%s cycle=%s", var_key, cycle_str)
        try:
            H = Herbie(date_str, model="gfs", product="pgrb2.0p25", fxx=cycle.fxx, verbose=False)
            ds = H.xarray(search_string)
        except Exception as exc:
            raise GFSDownloadError(f"Failed to fetch GFS variable {var_key}: {exc}") from exc

        # Extract the DataArray — field name varies, fall back to first data variable
        if field_name in ds:
            da = ds[field_name]
        else:
            data_vars = [v for v in ds.data_vars]
            if not data_vars:
                raise GFSDownloadError(f"No data variables found in GFS dataset for {var_key}")
            da = ds[data_vars[0]]

        # Identify spatial dimension names (herbie uses 'latitude'/'longitude')
        lat_dim = "latitude" if "latitude" in da.dims else "y"
        lon_dim = "longitude" if "longitude" in da.dims else "x"

        # GFS uses 0–360° longitudes; normalize to -180/180 so bbox clipping works
        if float(da[lon_dim].max()) > 180:
            import numpy as np
            lon_norm = (da[lon_dim].values + 180) % 360 - 180
            da = da.assign_coords({lon_dim: lon_norm}).sortby(lon_dim)

        da = da.rio.set_spatial_dims(x_dim=lon_dim, y_dim=lat_dim)
        da = da.rio.write_crs("EPSG:4326")

        try:
            clipped = da.rio.clip_box(
                minx=bbox_west, miny=bbox_south, maxx=bbox_east, maxy=bbox_north
            )
        except Exception as exc:
            raise GFSDownloadError(f"Failed to clip GFS variable {var_key} to bbox: {exc}") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        clipped.rio.to_raster(str(output_path))
        logger.info("Saved GFS %s → %s", var_key, output_path)

        return GFSVariableMetadata(
            variable=var_key,
            asset_type=asset_type,
            file_path=str(output_path),
            crs="EPSG:4326",
            resolution_deg=0.25,
            band_count=1,
            dtype=str(clipped.dtype),
            file_size_bytes=output_path.stat().st_size,
            cycle=cycle_str,
            search_string=search_string,
        )
